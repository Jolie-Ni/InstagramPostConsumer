from dataclasses import asdict, dataclass
import time
import shutil
import json
import boto3
from botocore.exceptions import ClientError
import re
import requests

# introduce redis cache
# key: post shortcode
# value: List<PlaceId>

# fix prompt next step

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

def get_caption_from_media_id(media_id):
    instagram_access_token = get_api_key("INSTAGRAM_GRAPH_API")
    instagram_graph_api = "https://graph.instagram.com/v20.0/" + media_id + "?fields=caption&access_token=" + instagram_access_token
    print(instagram_graph_api)
    response = requests.get(instagram_graph_api)

    if response.status_code == 200:
      data = response.json()
      return data["caption"]
    else:
      print(f"Failed to fetch from instagram graph API: {response.status_code}")
      return None

def lambda_handler(event, context):
    print(event)
    sqs = boto3.client('sqs')
    queue_url = "https://sqs.us-east-1.amazonaws.com/310780496713/openai_api.fifo"
    records = event["Records"]
    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        sender = bodyJson["sender"]
        media_id = bodyJson["media_id"]
        mid = bodyJson["mid"]
        print("sender: " + sender + ", media_id: " + media_id)
        # get post from instagram graph api
        caption = get_caption_from_media_id(media_id)
        if (caption == None):
            return
        
        message_body = {
            "mid": mid,
            "sender": sender,
            "caption": caption
        }
        
        print("sending message" + json.dumps(message_body))
        sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message_body), MessageGroupId=sender)
        
