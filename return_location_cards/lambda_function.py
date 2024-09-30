
def lambda_handler(event, context):
    print(event)
    records = event["Records"]
    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        placeIds = bodyJson["placeIds"]
        for placeId in placeIds:
            # return templates



# each place is a separate card and can be added to google map separately
# solve the app redirect issue
# find out ways to add places to google map at once
