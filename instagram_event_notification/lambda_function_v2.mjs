import { SQSClient, SendMessageCommand } from "@aws-sdk/client-sqs";

const sqsClient = new SQSClient({ region: "us-east-1" });
const instagram_graph_api_queue =
  "https://sqs.us-east-1.amazonaws.com/310780496713/get_post_from_media_id.fifo";
const open_ai_queue_url =
  "https://sqs.us-east-1.amazonaws.com/310780496713/openai_api.fifo";

const getMediaIdFromUrl = (url) => {
  // sample url: https://lookaside.fbsbx.com/ig_messaging_cdn/?asset_id=18275099551246187&signature=AbwHAkucILuUY3fW1SCuR51rhevAWXn8HuIFrOciab1XBc0lu-LE7BiPFgzbx3Pf2cM23YfRfW5cp4bUPvLTwJ_1fjkCtrzUwZYCGqd7e1McwpbvadU5bhxZaZ7QXgyVsVb1PJqWjofYno90ygQ7zhXFyXsgRSTkYLgvn4mRZ68tyWjTpl1QXcsZfpdYC0zyLaBmd5d-aHMdOcSNl8j_YfYwMBJfUi48
  const regex = /asset_id=([\d]+)/;

  const match = url.match(regex);

  if (match && match[1]) {
    return match[1];
  } else {
    return "";
  }
};

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
      if (media_id == "") {
        console.log("couldn't find media_id, dropping this event");
        return {
          statusCode: 200,
          body: JSON.stringify(event),
        };
      }

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
        body: JSON.stringify(event),
      };
    }

    let messageParams = {
      MessageGroupId: sender,
      MessageBody: JSON.stringify(messageBody),
      QueueUrl: queueUrl,
    };

    try {
      await sqsClient.send(new SendMessageCommand(messageParams));
      console.log("sending to SQS" + JSON.stringify(messageParams));
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
