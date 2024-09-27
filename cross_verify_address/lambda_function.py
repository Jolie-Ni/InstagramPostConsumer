from dataclasses import asdict, dataclass
import time
import json
import boto3
from botocore.exceptions import ClientError
import requests

@dataclass
class Location:
    lng: float
    lat: float

@dataclass
class ValidAddress:
    address: str
    location: Location 

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

def name_and_address_matched(name_lng_lat, address_lng_lat) -> bool: 
    if abs(name_lng_lat.lat - address_lng_lat.lat)< 0.001 and abs(name_lng_lat.lng - address_lng_lat.lng) < 0.001:
        return True
    else:
        return False

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
        
def write_to_DB(sender, mid, businessName, verifiedAddress):
    dynamodb = boto3.client('dynamodb')
    businessAddress = verifiedAddress.address if verifiedAddress is not None else None
    businessLocation = asdict(verifiedAddress.location) if verifiedAddress is not None else None

    item = {
        'message_id': {'S': mid},
        'instagram_id': {'S': sender},
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


# need to update the table we are writing to
# need a new table to construct db structure
# partition key: sender
# sort key: mid
def lambda_handler(event, context):
    print(event)
    records = event["Records"]
    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        businessAddresses = bodyJson["businessAddresses"]
        businessNames = bodyJson["businessNames"]
        sender = bodyJson["body"]
        mid = bodyJson["mid"]
        print("sender: " + bodyJson["sender"])
        

        for i in range(len(businessAddresses)):
            verified_address = cross_verify_address(business_name=businessNames[i], business_address=businessAddresses[i])
            write_to_DB(sender, mid, businessNames[i] , verified_address)

