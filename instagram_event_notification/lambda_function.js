import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import {
  DynamoDBDocumentClient,
  ScanCommand,
  PutCommand,
  GetCommand,
  DeleteCommand,
} from "@aws-sdk/lib-dynamodb";

import { SQSClient, SendMessageCommand } from "@aws-sdk/client-sqs";

const dynamoDBClient = new DynamoDBClient({});
const sqsClient = new SQSClient({ region: "us-east-1" });
const dynamo = DynamoDBDocumentClient.from(dynamoDBClient);

const tableName = "instagram_message";
const sqsQueueUrl = "https://sqs.us-east-1.amazonaws.com/310780496713/instaloader_processing_queue.fifo";

export const handler = async (event, context) => {
  console.log(`Webhook event received`);
  let eventBody = JSON.parse(event["body"]);
  // let eventBody = event["body"];
  let eventObject = eventBody["object"];
  console.log(`Event Object: ${eventObject}`);
  
  // assumes we only subscribe to instagram message webhook event
  if (eventObject === 'instagram') {
    let messaging = eventBody["entry"][0]["messaging"][0];
    let sender = messaging["sender"]["id"];
    console.log(`Sender: ${sender}`);
    let postUrl = messaging["message"]["text"]
    console.log("postUrl: " + postUrl);
    // assume they only send one
    //let attachment = messaging["message"]["attachments"][0]
    //let attachmentType = attachment["type"]
    //console.log("attachmentType: " + attachmentType)
    //let mediaId
    //if (attachmentType === "ig_reel") {
    //  mediaId = attachment["payload"]["reel_video_id"]
    //}
    //console.log("mediaId: " + mediaId)
    /*
    await dynamo.send(
          new PutCommand({
            TableName: tableName,
            Item: {
              aws_request_id: context.awsRequestId,
              instagram_id: sender,
              message_id: messageId,
              type: attachmentType,
              mediaId: mediaId
            },
          })
        );
        
    */
    
    // extract post shortcode
    const regex = /https:\/\/www\.instagram\.com\/(p|reel)\/([^\/]+)/ ;
    const match = postUrl.match(regex);
    let shortCode

    if (match) {
      shortCode = match[2]
      console.log(shortCode)
      const messageBody = {
        "requestId": context.awsRequestId,
        "sender": sender,
        "shortCode": shortCode
      }
      
      const messageParams = {
        MessageGroupId: sender,
        MessageBody: JSON.stringify(messageBody),
        QueueUrl: sqsQueueUrl,
        MessageDeduplicationId: context.awsRequestId
      }
        
      try {
        await sqsClient.send(new SendMessageCommand(messageParams));
      } catch (error) {
        throw error;
      }
      
      return {
      statusCode: 200,
      body: `Post shortcode: ${shortCode}`
    }
    } else {
      console.log('Post ID not found');
      return {
        statusCode: 200,
        body: `${JSON.stringify(eventBody)} EVENT RECEIVED`
      }
    }
  } else {
    console.log(`Invalid Event`)
    return {
      statusCode: 200,
      body: JSON.stringify(event)
    }
  }
};
