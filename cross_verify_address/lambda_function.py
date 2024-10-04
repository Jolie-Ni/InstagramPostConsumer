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
    placeId: str
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
    if abs(name_lng_lat.lat - address_lng_lat.lat)< 0.01 and abs(name_lng_lat.lng - address_lng_lat.lng) < 0.01:
        return True
    else:
        return False

def cross_verify_address(business_name, business_address) -> ValidAddress:
    google_geocoding_api = "https://maps.googleapis.com/maps/api/geocode/"
    output_format = "json"
    google_api_key = get_api_key("GOOGLE_API_KEY")
    # call google geocoding API
    nameResponse = requests.get(f"{google_geocoding_api}{output_format}?address={business_name}&key={google_api_key}")
    addressResponse = requests.get(f"{google_geocoding_api}{output_format}?address={business_address}&key={google_api_key}")

    result = None
    # if one response came back empty or having more than 1, use the other
    if nameResponse.status_code == 200 and addressResponse.status_code == 200:
        # look at actual results
        nameResponseJson = nameResponse.json()
        addressResponseJson = addressResponse.json()
        if nameResponseJson["status"] == 'OK' and addressResponseJson["status"] == 'OK':
            data_from_name = nameResponseJson["results"]
            data_from_address = addressResponseJson["results"]
            if len(data_from_name) != 0 and len(data_from_address) != 0:
                if len(data_from_name) == 1 and len(data_from_address) == 1:
                    location_from_name = Location(data_from_name[0]['geometry']['location']['lng'], data_from_name[0]['geometry']['location']['lat']) 
                    location_from_address = Location(data_from_address[0]['geometry']['location']['lng'], data_from_address[0]['geometry']['location']['lat'])
                    if (name_and_address_matched(location_from_name, location_from_address)):
                      # if match, store to DB
                      print("LOG::Name and address goecoding matched")
                      return ValidAddress(data_from_name[0]["place_id"], data_from_name[0]['formatted_address'], location_from_name)
                    else:
                      print("LOG::Name and address geocoding mismatch")
                      return None
                elif len(data_from_name) == 1:
                    result = nameResponse
                    print("LOG::Found unique name geocoding and non-unique address geo-coding, use Name")
                elif len(data_from_address) == 1:
                    result = addressResponse
                    print("LOG::Found unique address geocoding and non-unique name geo-coding, use Address")
                else:
                    print("LOG::Both geocoding requests came back non unique")
                    return None            
            elif len(data_from_name) != 0:
                    result = nameResponse
                    print("LOG::Find non-empty name geocoding, empty address geocoding, use Name")
            elif len(data_from_address) != 0:
                    result = addressResponse
                    print("LOG::Find non-empty address geocoding, empty name geocoding, use Address")
            else:
                print("LOG::Both geocoding requests results came back empty")
                return None         
        elif nameResponseJson["status"] == 'OK':
            result = nameResponse
            print("LOG::Only name geocoding request status = OK, use Name")
        elif addressResponseJson["status"] == 'OK':
            result = addressResponse
            print("LOG::Only address geocoding request status = OK, use Address")
        else:
            print("LOG::Neither request status, name geocoding and address geocoding, came back as OK")
            return None
    elif addressResponse.status_code == 200:
        result = addressResponse
        print("LOG::Only address geocoding request suceed, use Address")
    elif nameResponse.status_code == 200:    
        result = nameResponse
        print("LOG::Only name geocoding request suceed, use Name")
    else:
        print("LOG::Both name geocoding and address geocoding requests failed")
        return None
    
    resultJson = result.json()
    if resultJson["status"] != 'OK':
        print("LOG::Request status != OK")
        return None
    else:
      result_data = resultJson["results"][0]
      location_from_result = Location(result_data['geometry']['location']['lng'], result_data['geometry']['location']['lat'])
      print("LOG::Found a valid address")
      return ValidAddress(result_data["place_id"], result_data['formatted_address'], location_from_result)

        
def write_to_DB(sender, mid, businessName, verifiedAddress):
    dynamodb = boto3.client('dynamodb')
    businessAddress = verifiedAddress.address if verifiedAddress is not None else None
    businessLocation = asdict(verifiedAddress.location) if verifiedAddress is not None else None
    placeId = verifiedAddress.placeId if verifiedAddress is not None else None

    item = {
        'message_id': {'S': mid},
        'instagram_id': {'S': sender},
        'place_id': {'S': placeId},
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
    
    if (businessAddress is None) and (businessLocation is None):
        print("Both address and name are empty, drop this event")
    else:
        print("send to db: " + json.dumps(item))
        dynamodb.put_item(
            TableName='instagram_locations_v2',
            Item=item
        )


# need to update the table we are writing to
# need a new table to construct db structure
# partition key: sender
# sort key: mid
def lambda_handler(event, context):
    print(event)
    records = event["Records"]
    sqs = boto3.client('sqs')
    queue_url="https://sqs.us-east-1.amazonaws.com/310780496713/send_instagram_location_cards.fifo"
    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        businessAddresses = bodyJson["businessAddresses"]
        businessNames = bodyJson["businessNames"]
        sender = bodyJson["sender"]
        mid = bodyJson["mid"]

        placeIds = []
        bAddresses = []
        for i in range(len(businessAddresses)):
            verified_address = cross_verify_address(business_name=businessNames[i], business_address=businessAddresses[i])
            print("writing to db")
            write_to_DB(sender, mid, businessNames[i] , verified_address)
            if (verified_address):
                placeIds.append(verified_address.placeId)
                bAddresses.append(verified_address.address)

        if len(placeIds) != 0:
            message_body = {
              "sender": sender,
              # adding this to avoid sqs treating it as duplicate message
              "mid": mid,
              "businessAddresses": bAddresses,
              "placeIds": placeIds
            }
            sqs.send_message(MessageGroupId=sender, QueueUrl=queue_url, MessageBody=json.dumps(message_body))       
            

