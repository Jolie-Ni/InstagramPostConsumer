from dataclasses import asdict, dataclass
import time
from instaloader import Instaloader, Post
import os
from glob import glob
from os.path import expanduser
from platform import system
from sqlite3 import OperationalError, connect
import shutil
import json
import boto3
from botocore.exceptions import ClientError
from openai import OpenAI
import re
import requests

def lambda_handler(event, context):

    records = event["Records"]
    for record in records:
        body = record["body"]
        print(body)
        bodyJson = json.loads(body)
        shortCode = bodyJson["shortCode"]
        print("sender: " + bodyJson["sender"] + ", shortCode: " + shortCode)
        post = Post.from_shortcode(L.context, shortCode)
        print(post.caption)
        addresses, businessNames = get_address(post.caption)
        if len(addresses) != len(businessNames):
            print("Error: Addresses and Name length mismatched")
        else:
            for i in range(len(addresses)):
                verified_address = cross_verify_address(business_name=businessNames[i], business_address=addresses[i])
                write_to_DB(bodyJson["requestId"] + ':' + str(i), bodyJson["sender"], shortCode, businessNames[i] , verified_address)

    print(event)
