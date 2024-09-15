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
    
def get_openai_api_key(): 
    secret_name = "OPENAI_API_KEY"
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
    print("openai API_KEY: " + secret);
    return json.loads(secret)["OPENAI_API_KEY"]
        
def get_openai_client():
    
    return OpenAI(
        api_key = get_openai_api_key()
    )
        
def extract_an_address(text):
    pattern = r'<Address: (.*?)>'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return ""

def extract_name(text):
    pattern = r'\[Name: (.*?)\]'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return ""

def get_address(caption): 
    # info from caption
    # if not available in caption, ignore

    prompt_text = 'extract geo location information from the below paragraph and give me back an address that is searable in google map. Give me the address enclosed in <> and name of this place in []. Give me response strictly follow the pattern: <Address: >, [Name: ] ' + '"' + caption + '"'
    
    openai_client = get_openai_client()
    chatgpt_response = openai_client.chat.completions.create(
        messages=[
            {   "role": "system",
                "content": "you are an expert in reading text in different languages and parse out location information + business name from the text"
            },
            {
                "role": "assistant",
                "content": "Yes, I can help with parsing text in different languages to extract location information and business names. If you provide the text you want analyzed, I can assist in identifying these details for you. How can I assist you with this task?"
            },
            {
                "role": "user",
                "content": 'extract geo location information from the below paragraph and give me back an address that is searable in google map. Give me the address enclosed in <> and name of this place in []. Give me response strictly follow the pattern: <Address: >, [Name: ] ' + '"' + caption + '"'
            }
        ],
        model="gpt-4o"
    )
    print(chatgpt_response)
    response_text = chatgpt_response.choices[0].message.content
    print("response: " + response_text)

    # parse out link

    return extract_an_address(response_text), extract_name(response_text)

def write_to_DB(requestId, sender, shortCode, address, businessName):
    dynamodb = boto3.client('dynamodb')
    dynamodb.put_item(
        TableName='instagram_message',
        Item={
            'aws_request_id': {'S': requestId },
            'instagram_id': {'S': sender},
            'shortCode': {'S': shortCode},
            'address': {'S': address},
            'name': {'S': businessName}
        }
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
        address, businessName = get_address(post.caption)
        print("google map url: " + address)
        print("businessName: " + businessName)
        # save to dynamoDB
        write_to_DB(bodyJson["requestId"], bodyJson["sender"], shortCode, address, businessName);

    print(event)

# post location currently unavailable due to a bug: 
# https://github.com/instaloader/instaloader/issues/2215
'''
post_location = post.location
if (post_location) :
    print("location:" + post_location.name)
'''

'''
    

    print("caption:" + post.caption)
    print("comments count: " + str(post.comments))
'''
