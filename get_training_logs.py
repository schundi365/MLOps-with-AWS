#!/usr/bin/env python3
"""
Get actual training logs from CloudWatch.
"""

import boto3
import sys
from datetime import datetime

def get_training_logs(job_name, region='us-east-1'):
    """Get training logs from CloudWatch."""
    
    logs = boto3.client('logs', region_name=region)
    
    # Log group name for SageMaker training jobs
    log_group = '/aws/sagemaker/TrainingJobs'
    
    print("\n" + "="*70)
    print("FETCHING TRAINING LOGS")
    print("="*70)
    print(f"Job: {job_name}")
    print(f"Log Group: {log_group}")
    print()
    
    try:
        # Get log streams for this job
        response = logs.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=job_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not response['logStreams']:
            print("No log streams found for this job.")
            print("\nPossible reasons:")
            print("1. Job hasn't started yet")
            print("2. Job name is incorrect")
            print("3. Logs haven't been created yet")
            return
        
        print(f"Found {len(response['logStreams'])} log streams")
        print()
        
        # Get logs from each stream
        for stream in response['logStreams']:
            stream_name = stream['logStreamName']
            print("="*70)
            print(f"Log Stream: {stream_name}")
            print("="*70)
            
            try:
                # Get log events
                log_response = logs.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    startFromHead=True,
                    limit=100
                )
                
                events = log_response['events']
                if not events:
                    print("(No log events)")
                    continue
                
                # Print log events
                for event in events:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].rstrip()
                    print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
                
                print()
                
            except Exception as e:
                print(f"Error reading log stream: {e}")
                print()
        
        print("="*70)
        
    except logs.exceptions.ResourceNotFoundException:
        print(f"Log group '{log_group}' not found.")
        print("\nThis usually means no training jobs have been run yet.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nTry viewing logs in AWS Console:")
        print(f"https://console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups/log-group/$252Faws$252Fsagemaker$252FTrainingJobs")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python get_training_logs.py <job-name> [region]")
        print("Example: python get_training_logs.py movielens-training-20260120-174840-354 us-east-1")
        sys.exit(1)
    
    job_name = sys.argv[1]
    region = sys.argv[2] if len(sys.argv) > 2 else 'us-east-1'
    
    get_training_logs(job_name, region)
