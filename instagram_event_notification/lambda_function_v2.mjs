import { DynamoDBClient } from "@aws-sdk/client-dynamodb";
import { DynamoDBDocumentClient } from "@aws-sdk/lib-dynamodb";

import { SQSClient, SendMessageCommand } from "@aws-sdk/client-sqs";

const sqsClient = new SQSClient({ region: "us-east-1" });
const instagram_graph_api_queue =
  "https://sqs.us-east-1.amazonaws.com/310780496713/get_post_from_media_id.fifo";
const open_ai_queue_url =
  "https://sqs.us-east-1.amazonaws.com/310780496713/openai_api.fifo";

export const handler = async (event, context) => {
  console.log(`Webhook event received`);
  let eventBody = JSON.parse(event["body"]);
  // let eventBody = event["body"];
  let eventObject = eventBody["object"];
  console.log(`Event Object: ${eventObject}`);

  // assumes we only subscribe to instagram message webhook event
  if (eventObject === "instagram") {
    let messaging = eventBody["entry"][0]["messaging"][0];
    let sender = messaging["sender"]["id"];
    console.log(`Sender: ${sender}`);
    let mid = messaging["message"]["mid"];
    let attachment = messaging["message"]["attachments"][0];
    let attachment_type = attachment["type"];
    let messageBody;
    let queueUrl;
    if (attachment_type == "ig_reel") {
      let caption = messaging["message"]["attachments"][0]["payload"]["title"];
      // send to open_ai_queue
      messageBody = {
        mid: mid,
        sender: sender,
        caption: caption,
      };

      queueUrl = open_ai_queue_url;
    } else if (attachment_type == "share") {
      // send to instagram_graph_api_queue
      let media_url = attachment["payload"]["url"];
      let media_id = getMediaIdFromUrl(media_url);

      messageBody = {
        mid: mid,
        sender: sender,
        media_id: media_id,
      };

      queueUrl = instagram_graph_api_queue;
    } else {
      // response with "To use our tool, please share a post or reel containing locations you are interested in with us".
      return {
        statusCode: 200,
        body: `Post shortcode: ${shortCode}`,
      };
    }

    let messageParams = {
      MessageGroupId: sender,
      MessageBody: JSON.stringify(messageBody),
      QueueUrl: queueUrl,
      MessageDeduplicationId: mid,
    };

    try {
      await sqsClient.send(new SendMessageCommand(messageParams));
    } catch (error) {
      throw error;
    }
  } else {
    console.log(`Not an instagram event, dropped`);
    return {
      statusCode: 200,
      body: JSON.stringify(event),
    };
  }
};
