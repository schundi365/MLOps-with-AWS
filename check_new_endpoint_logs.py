"""
Check logs for the new endpoint to see if the fix worked.
"""

import boto3
from datetime import datetime

def check_new_endpoint_logs():
    """Check logs for the newly deployed endpoint."""
    
    logs_client = boto3.client('logs', region_name='us-east-1')
    
    # New endpoint name
    endpoint_name = 'movielens-endpoint-20260122-162230-4567'
    log_group = f'/aws/sagemaker/Endpoints/{endpoint_name}'
    
    print(f"\n{'='*70}")
    print(f"CHECKING NEW ENDPOINT LOGS: {endpoint_name}")
    print(f"{'='*70}\n")
    
    try:
        # Get all log streams
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        print(f"Found {len(response['logStreams'])} log streams\n")
        
        # Check each log stream
        for stream in response['logStreams']:
            stream_name = stream['logStreamName']
            print(f"\nStream: {stream_name}")
            print(f"{'='*70}")
            
            # Get log events
            events_response = logs_client.get_log_events(
                logGroupName=log_group,
                logStreamName=stream_name,
                startFromHead=True,
                limit=200
            )
            
            events = events_response['events']
            if not events:
                print("  No log events found")
                continue
            
            # Print all events
            for event in events:
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                message = event['message']
                print(f"[{timestamp}] {message}")
        
        print(f"\n{'='*70}\n")
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"Log group not found: {log_group}")
        print("The endpoint may not have been created yet or logs haven't been generated.")
    except Exception as e:
        print(f"Error checking logs: {e}")

if __name__ == '__main__':
    check_new_endpoint_logs()
