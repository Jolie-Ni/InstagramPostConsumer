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
        
def extract_all_http_links(text):
    pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
    return re.findall(pattern, text)

def get_google_map_urls(caption): 
    # info from caption
    # if not available in caption, ignore
    
    openai_client = get_openai_client()
    chatgpt_response = openai_client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": 'extract geo location information from the below paragraph and give me back a pin on google map, you only need to return me a google map link.' + '"' + caption + '"'
            }
        ],
        model="gpt-3.5-turbo"
    )
    print(chatgpt_response)
    #response_text = chatgpt_response["choices"][0]["message"]["content"]
    #print(response_text)
    #print("response: " + response_text)

    # parse out link

    #return extract_all_http_links(response_text)
    return ""
    

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
        urls = get_google_map_urls(post.caption)
        print("google map url: " + urls)
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
