from dataclasses import asdict, dataclass
import time
from instaloader import Instaloader, Post
import os
from glob import glob
from os.path import expanduser
from platform import system
from sqlite3 import OperationalError, connect
import shutil
import json
import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
import re
import requests

def get_cookiefile():
    cookiePath = os.environ['LAMBDA_TASK_ROOT'] + "/cookies.sqlite"
    cookiefiles = glob(expanduser(cookiePath))
    if not cookiefiles:
        raise SystemExit("No Firefox cookies.sqlite file found. Use -c COOKIEFILE.")
    return cookiefiles[0]

def import_session(cookiefile, sessionfile):
    os.chdir("/tmp")
    shutil.copyfile('/var/task/cookies.sqlite', '/tmp/cookies.sqlite')
    # switch to a folder I have write access to
    conn = connect(f"file:/tmp/cookies.sqlite?immutable=1", uri=True)
    try:
        cookie_data = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE baseDomain='instagram.com'"
        )
    except OperationalError:
        cookie_data = conn.execute(
            "SELECT name, value FROM moz_cookies WHERE host LIKE '%instagram.com'"
        )
    L = Instaloader(max_connection_attempts=1)
    L.context._session.cookies.update(cookie_data)
    username = L.test_login()
    if not username:
        raise SystemExit("Not logged in. Are you logged in successfully in Firefox?")
    print("Imported session cookie for {}.".format(username))
    L.context.username = username
    print("username:" + username)
    L.save_session_to_file(sessionfile)
    return L

def get_api_key( secret_name): 
    region_name = "us-east-1"

    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name,
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    secret = get_secret_value_response['SecretString']
    print(f"{secret_name}: {secret}")
    return json.loads(secret)[secret_name]

def get_openai_client():
    open_ai_secret_name = "OPENAI_API_KEY"
    return OpenAI(
        api_key = get_api_key(open_ai_secret_name)
    )
        
def extract_addresses(text):
    pattern = r'<Address: (.*?)>'
    match = re.findall(pattern, text)
    if match:
        return match
    else:
        return []

def extract_names(text):
    pattern = r'\[Name: (.*?)\]'
    match = re.findall(pattern, text)
    if match:
        return match
    else:
        return []

def get_address(caption): 

    # info from caption
    # if not available in caption, ignore
    
    openai_client = get_openai_client()
    chatgpt_response = openai_client.chat.completions.create(
        messages=[
            {   "role": "system",
                "content": "you are an expert in reading text in different languages and parse out one or multiple locations' information + business name from the text. Give me response strictly follow the pattern: <Address: >, [Name: ]." +  
                "Make sure to separate each Address Name pair with a new line." +
                "For each location, if there is no business name found but address is given. Just put the same content in both address and name" +
                "If neither is found, put N/A in both"
            },
            {
                "role": "assistant",
                "content": "Understood! Please provide the text you'd like me to process, and I'll parse out the locations and business names accordingly."
            },
            {
                "role": "user",
                "content": '"' + caption + '"'
            }
        ],
        model="gpt-4o"
    )
    print(chatgpt_response)
    response_text = chatgpt_response.choices[0].message.content
    print("response: " + response_text)

    # parse out link

    return extract_addresses(response_text), extract_names(response_text)

def name_and_address_matched(name_lng_lat, address_lng_lat) -> bool: 
    if abs(name_lng_lat.lat - address_lng_lat.lat)< 0.001 and abs(name_lng_lat.lng - address_lng_lat.lng) < 0.001:
        return True
    else:
        return False
    
@dataclass
class Location:
    lng: float
    lat: float

@dataclass
class ValidAddress:
    address: str
    location: Location 

def cross_verify_address(business_name, business_address) -> ValidAddress:
    google_geocoding_api = "https://maps.googleapis.com/maps/api/geocode/"
    output_format = "json"
    google_api_key = get_api_key("GOOGLE_API_KEY")
    # call google geocoding API
    response1 = requests.get(f"{google_geocoding_api}{output_format}?address={business_name}&key={google_api_key}")

    if business_name and not business_address:
        responseJson = response1.json()
        print(responseJson)
        if responseJson['status'] != 'OK':
            print("No address found for: " + business_name)
            return None
        # assume one result comes back for mvp
        data_from_name = responseJson['results'][0]
        location_from_name = Location(data_from_name['geometry']['location']['lng'], data_from_name['geometry']['location']['lat'])
        return ValidAddress(data_from_name['formatted_address'], location_from_name)

    response2 = requests.get(f"{google_geocoding_api}{output_format}?address={business_address}&key={google_api_key}")

    if response1.status_code != 200:
        print("Fetch address for: " + business_name + " failed")
        return None
    
    if response2.status_code != 200:
        print("Fetch address found for: " + business_address + " failed")
        return None

    if response1.status_code == 200 and response2.status_code == 200:
        # get long + lat for both address and name
        responseJson = response1.json()
        print(responseJson)
        if responseJson['status'] != 'OK':
            print("No address found for: " + business_name)
            return None
        # assume one result comes back for mvp
        data_from_name = responseJson['results'][0]
        location_from_name = Location(data_from_name['geometry']['location']['lng'], data_from_name['geometry']['location']['lat']) 
        responseJson = response2.json()
        if responseJson['status'] != 'OK':
            print("No address found for: " + business_address)
            return None
        data_from_address = responseJson['results'][0]
        location_from_address = Location(data_from_address['geometry']['location']['lng'], data_from_address['geometry']['location']['lat'])
        if (name_and_address_matched(location_from_name, location_from_address)):
            # if match, store to DB
            return ValidAddress(data_from_name['formatted_address'], location_from_name)
        else:
            return None
        
def clean_item_by_remove_None_fields(item): 
    return {k: v for k, v in item.items() if v is not None}        

def write_to_DB(requestId, sender, shortCode, businessName, verifiedAddress):
    dynamodb = boto3.client('dynamodb')
    businessAddress = verifiedAddress.address if verifiedAddress is not None else None
    businessLocation = asdict(verifiedAddress.location) if verifiedAddress is not None else None

    item = {
        'instagram_id': {'S': sender},
        'request_id': {'S': requestId},
        'shortCode': {'S': shortCode},
        'businessName': {'S': businessName},
        'isValid': {'BOOL': verifiedAddress != None},
    }
    
    if businessAddress is not None: 
        item['businessAddress'] = {'S': businessAddress}
    if businessLocation is not None:    
        item['businessLocation'] = {'M': {
            'lng': {'N': str(businessLocation['lng'])},  # Must convert float to string and wrap in 'N'
            'lat': {'N': str(businessLocation['lat'])}    # Must convert float to string and wrap in 'N'
        }}
        
    item['createdAt'] = {'N': str(int(time.time()))}

    dynamodb.put_item(
        TableName='instagram_locations',
        Item=item
    )
    

def lambda_handler(event, context):
    L = import_session(get_cookiefile(), "randaway_travel")
    records = event["Records"]
    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        shortCode = bodyJson["shortCode"]
        print("sender: " + bodyJson["sender"] + ", shortCode: " + shortCode)
        post = Post.from_shortcode(L.context, shortCode)
        print(post.caption)
        addresses, businessNames = get_address(post.caption)
        if addresses.length != businessNames.length:
            print("Error: Addresses and Name length mismatched")
        else:
            for i in range(len(addresses)):
                verified_address = cross_verify_address(business_name=businessNames[i], business_address=addresses[i])
                write_to_DB(bodyJson["requestId"], bodyJson["sender"], shortCode, businessNames[i] , verified_address)

    print(event)


caption = '''
"Save this 7D Osaka and West Kansai Itinerary for your next visit to Japan! 🗼

Our trip to Osaka and West Kansai was everything we dreamed about - we played with Mario, fed some deers, had mouth-watering local cuisines and explored the city in kimonos. Here's everything we did in our 7 days:

Day 1: Osaka
- Walk around Shinsaibashi-Suji Shopping Street or Den Den Town
- Dinner at Dotonbori Street

Day 2: Osaka
- Explore Osaka Castle
- Immerse yourself at teamLab Botanical Garden Osaka 

Day 3: Universal Studios Japan
- Geek out at Super Nintendo World
- Cast a spell at The Wizarding World of Harry Potter

Day 4: Nara
- Feed deers at Nara park

Day 5: Okayama, Kurashiki and Kobe
- Walk along the famous Kurashiki Canal
- Stroll in the Korakuen Garden
- Feast on Kobe beef

Day 6: Kyoto
- Explore the city in a kimono
- Count the number of Torii gates at Fushimi Inari shrine

Day 7: Kyoto
- Explore the Arashiyama bamboo forest
- Feast at Nishiki market

📸: @eel_nadnerb @tee_nie
⁠
📍Click our link in bio to check out the full article!

Share your favourite travel photos with #thetravelintern to be featured!"
'''
# addresses, businessNames = get_address(caption)
# if len(addresses) != len(businessNames):
#     print("Error: Addresses and Name length mismatched")
# else:    
#     for i in range(len(addresses)):
#         verified_address = cross_verify_address(business_name=businessNames[i], business_address=addresses[i])
#         write_to_DB(f'test{i}', f'test{i}', "test", businessNames[i] , verified_address)


'''
post_location = post.location
if (post_location) :
    print("location:" + post_location.name)
'''

'''
    

    print("caption:" + post.caption)
    print("comments count: " + str(post.comments))
'''


