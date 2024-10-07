import json
import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
import re

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


def lambda_handler(event, context):
    print(event)
    records = event["Records"]
    queue_url = "https://sqs.us-east-1.amazonaws.com/310780496713/google_map_decoding_api.fifo"
    reply_queue_url = "https://sqs.us-east-1.amazonaws.com/310780496713/send_instagram_location_cards.fifo"
    sqs = boto3.client('sqs')
    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        caption = bodyJson["caption"]
        mid = bodyJson["mid"]
        sender = bodyJson["sender"]
        print("sender: " + sender)
        print("caption: " + caption)
        addresses, businessNames = get_address(caption)

        if len(addresses) == 0 or len(businessNames) == 0:
            # send to error message queue
            message_body = {
              "sender": sender,
              "messageType": "error",
            }

            # short circuit here
            sqs.send_message(MessageGroupId=sender, QueueUrl=reply_queue_url, MessageBody=json.dumps(message_body))       
        if len(addresses) != len(businessNames):
            print("Error: Addresses and Name length mismatched")
            message_body = {
              "sender": sender,
              "messageType": "error",
            }

            # short circuit here
            sqs.send_message(QueueUrl=reply_queue_url,MessageBody=json.dumps(messageBody),MessageGroupId=sender)
        else:
            # send to cross verify queue
            for i in range(len(addresses)):
                messageBody = {
                            "mid": mid,
                            "sender": sender,
                            "businessName": businessNames[i],
                            "businessAddress": addresses[i]
                }
                print("sending message" + json.dumps(messageBody))
                sqs.send_message(QueueUrl=queue_url,MessageBody=json.dumps(messageBody),MessageGroupId=sender)