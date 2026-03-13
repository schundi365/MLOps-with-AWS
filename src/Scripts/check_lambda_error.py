#!/usr/bin/env python3
"""Check Lambda evaluation function logs for errors."""

import boto3
import json
from datetime import datetime, timedelta

def main():
    region = 'us-east-1'
    function_name = 'movielens-model-evaluation'
    
    print("\n" + "="*70)
    print("LAMBDA FUNCTION LOGS - Last 10 Minutes")
    print("="*70)
    print()
    
    logs_client = boto3.client('logs', region_name=region)
    
    # Get log group name
    log_group = f'/aws/lambda/{function_name}'
    
    try:
        # Get recent log streams
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not response['logStreams']:
            print("No log streams found")
            return
        
        # Get events from most recent stream
        stream_name = response['logStreams'][0]['logStreamName']
        print(f"Log Stream: {stream_name}")
        print()
        
        # Get log events
        events_response = logs_client.get_log_events(
            logGroupName=log_group,
            logStreamName=stream_name,
            limit=50,
            startFromHead=False
        )
        
        # Print events
        for event in events_response['events']:
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            message = event['message'].strip()
            print(f"[{timestamp}] {message}")
        
        print()
        print("="*70)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
