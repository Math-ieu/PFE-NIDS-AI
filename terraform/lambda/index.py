import json
import os

def handler(event, context):
    print("Received event: " + json.dumps(event, indent=2))
    for record in event['Records']:
        payload = record["body"]
        print(f"Processing flow: {payload}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Flow processed successfully')
    }
