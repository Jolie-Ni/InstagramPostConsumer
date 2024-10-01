
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

            # each place get place URL
            # get place first photo
            # get place reservation link



# each place is a separate card and can be added to google map separately
# solve the app redirect issue
# find out ways to add places to google map at once


'''
curl -X POST "https://graph.instagram.com/v20.0/17841463038230063/messages" \
-H "Authorization: Bearer IGQWRQdkVybFpjLXdRSzRFSGUyMDJ0SkVQYnFKTUptSkRLYllaQjVhN1NnckZAabHVvRldLUTZAPVVZACeTJpemMxMVNvMDRlNzRPbEFXSURyOXc3WWY0RTZAkSjFXNE43bGFHRXlsTmttY0k2WHpKZAUlIZAHZAhRFR4RlkZD" \
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