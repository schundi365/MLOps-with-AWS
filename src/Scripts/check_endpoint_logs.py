#!/usr/bin/env python3
"""Check CloudWatch logs for SageMaker endpoint to diagnose Worker died error."""

import boto3
from datetime import datetime, timedelta

def main():
    region = 'us-east-1'
    endpoint_name = 'movielens-endpoint-20260122-111111-355'
    
    logs_client = boto3.client('logs', region_name=region)
    
    print("\n" + "="*70)
    print(f"CHECKING ENDPOINT LOGS: {endpoint_name}")
    print("="*70)
    print()
    
    log_group = f'/aws/sagemaker/Endpoints/{endpoint_name}'
    
    try:
        # Get log streams
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        print(f"Log Group: {log_group}")
        print(f"Found {len(response['logStreams'])} log streams")
        print()
        
        # Get logs from most recent stream
        for stream in response['logStreams']:
            stream_name = stream['logStreamName']
            print(f"Stream: {stream_name}")
            print("="*70)
            
            # Get log events
            events_response = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                limit=100,
                startFromHead=False  # Get most recent
            )
            
            events = events_response['events']
            if not events:
                print("  No log events found")
                print()
                continue
            
            # Print last 50 events
            for event in events[-50:]:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message'].strip()
                print(f"[{timestamp}] {message}")
            
            print()
            print("="*70)
            print()
    
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"[!] Log group not found: {log_group}")
        print("    The endpoint may not have been created or logs not yet available")
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    print("="*70)

if __name__ == "__main__":
    main()
