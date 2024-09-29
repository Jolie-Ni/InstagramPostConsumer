
def lambda_handler(event, context):
    print(event)
    records = event["Records"]
    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        businessAddresses = bodyJson["businessAddresses"]
        businessNames = bodyJson["businessNames"]
        sender = bodyJson["sender"]
        mid = bodyJson["mid"]

        for i in range(len(businessAddresses)):
            verified_address = cross_verify_address(business_name=businessNames[i], business_address=businessAddresses[i])
            print("writing to db")
            write_to_DB(sender, mid, businessNames[i] , verified_address)