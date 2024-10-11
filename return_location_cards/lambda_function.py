import requests
import json
import boto3
from botocore.exceptions import ClientError
import urllib.parse

def get_message_url(sender: str) -> str:
  return f'https://graph.instagram.com/v20.0/{sender}/messages'

def get_api_key(secret_name): 
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

def lambda_handler(event, context):
    print(event)
    records = event["Records"]
    instagram_long_live_token = get_api_key("INSTAGRAM_GRAPH_API")
    headers = {
        "Authorization": f"Bearer {instagram_long_live_token}",
        "Content-Type": "application/json"
    }
    randawayInstaId = "17841463038230063"
    SEND_MESSAGE_URL = get_message_url(randawayInstaId)
    GOOGLE_URL_PREFIX = "https://www.google.com/maps/search/?api=1&"

    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        # 2 cases
        type = bodyJson["messageType"]
        text = ""
        sender = bodyJson["sender"]
        if type == "error":
           text = "Sorry, we are unable to parse out google map link/s from this post"

        else: 
          placeId = bodyJson["placeId"]
          businessAddress = bodyJson["businessAddress"]
          placeQuery = "query=" + urllib.parse.quote(businessAddress) + "&query_place_id=" + placeId
          text = GOOGLE_URL_PREFIX + placeQuery
        
        # error message
        data = {
          "recipient": {
            "id": sender
          },
          "message": {
            "text": text
          }
        }
        
        res = requests.post(SEND_MESSAGE_URL, headers=headers, json=data)
        print(res.json())


