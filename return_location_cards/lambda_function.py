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
        placeIds = bodyJson["placeIds"]
        sender = bodyJson["sender"]
        businessAddresses = bodyJson["businessAddresses"]

        for i in range(len(placeIds)):
            placeQuery = "query=" + urllib.parse.quote(businessAddresses[i]) + "&query_place_id=" + placeIds[i]
            data = {
                "recipient": {
                "id": sender
              },
              "message": {
                "text": GOOGLE_URL_PREFIX + placeQuery
              }
            }
            res = requests.post(SEND_MESSAGE_URL, headers=headers, json=data)
            print(res.json())

# https://developers.google.com/maps/documentation/places/web-service/op-overview#place_details_api
# place details API
# each place is a separate card and can be added to google map separately
# solve the app redirect issue
# find out ways to add places to google map at once


'''
curl -X POST "https://graph.instagram.com/v20.0/17841463038230063/messages" \
-H "Authorization: Bearer" \
-H "Content-Type: application/json" \
-d '{
  "recipient": {
    "id": "795372785581410"
  },
  "message": {
    "attachment": {
      "type": "template",
      "payload": {
        "template_type": "generic",
        "elements": [
          {
            "title": "jolie template",
            "image_url": "https://www.google.com/maps/place/Golden+Gate+Bridge/@37.8199286,-122.4782551,3a,75y,90t/data=!3m8!1e2!3m6!1sAF1QipN0-mJ4M1ftzod1vtrdwMyE2fmmqxGdPxnvQMH4!2e10!3e12!6shttps:%2F%2Flh5.googleusercontent.com%2Fp%2FAF1QipN0-mJ4M1ftzod1vtrdwMyE2fmmqxGdPxnvQMH4%3Dw114-h86-k-no!7i12000!8i9000!4m7!3m6!1s0x808586deffffffc3:0xcded139783705509!8m2!3d37.8199109!4d-122.4785598!10e5!16zL20vMDM1cDM?entry=ttu&g_ep=EgoyMDI0MDkyNS4wIKXMDSoASAFQAw%3D%3D",
            "subtitle": "golden gate bridge",
            "default_action": {
              "type": "web_url",
              "url": "https://www.google.com"
            },
            "buttons": [
              {
                "type": "web_url",
                "url": "https://www.google.com",
                "title": "Add to google map"
              },
              {
                "type": "postback",
                "title": "reserve",
                "payload": "reserve golden gate bridge"
              }
            ]
          },
          {
            "title": "jolie template",
            "image_url": "https://www.google.com/maps/place/Golden+Gate+Bridge/@37.8199286,-122.4782551,3a,75y,90t/data=!3m8!1e2!3m6!1sAF1QipN0-mJ4M1ftzod1vtrdwMyE2fmmqxGdPxnvQMH4!2e10!3e12!6shttps:%2F%2Flh5.googleusercontent.com%2Fp%2FAF1QipN0-mJ4M1ftzod1vtrdwMyE2fmmqxGdPxnvQMH4%3Dw114-h86-k-no!7i12000!8i9000!4m7!3m6!1s0x808586deffffffc3:0xcded139783705509!8m2!3d37.8199109!4d-122.4785598!10e5!16zL20vMDM1cDM?entry=ttu&g_ep=EgoyMDI0MDkyNS4wIKXMDSoASAFQAw%3D%3D",
            "subtitle": "golden gate bridge",
            "default_action": {
              "type": "web_url",
              "url": "https://www.google.com"
            },
            "buttons": [
              {
                "type": "web_url",
                "url": "https://www.google.com",
                "title": "Add to google map"
              },
              {
                "type": "postback",
                "title": "reserve",
                "payload": "reserve golden gate bridge"
              }
            ]
          }
        ]
      }
    }
  }
}'

'''