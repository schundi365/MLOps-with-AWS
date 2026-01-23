"""
Check detailed training logs for the current execution.
"""

import boto3
import time

def check_training_logs():
    """Get detailed training logs from CloudWatch."""
    
    sagemaker = boto3.client('sagemaker', region_name='us-east-1')
    logs = boto3.client('logs', region_name='us-east-1')
    
    print("\n" + "="*70)
    print("TRAINING JOB LOGS")
    print("="*70 + "\n")
    
    # Get the training job name
    training_job_name = 'movielens-training-20260123-112130'
    
    print(f"Training Job: {training_job_name}\n")
    
    # Get training job details
    try:
        response = sagemaker.describe_training_job(TrainingJobName=training_job_name)
        
        print(f"Status: {response['TrainingJobStatus']}")
        if 'SecondaryStatus' in response:
            print(f"Secondary Status: {response['SecondaryStatus']}")
        if 'FailureReason' in response:
            print(f"Failure Reason: {response['FailureReason']}")
        print()
        
    except Exception as e:
        print(f"Error getting training job details: {e}\n")
    
    # Get CloudWatch logs
    log_group = f"/aws/sagemaker/TrainingJobs"
    log_stream_prefix = training_job_name
    
    print("CloudWatch Logs:")
    print("-" * 70)
    
    try:
        # List log streams
        streams_response = logs.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=log_stream_prefix,
            descending=True,
            limit=5
        )
        
        if not streams_response.get('logStreams'):
            print("No log streams found yet. Training may not have started.")
            return
        
        # Get logs from the most recent stream
        for stream in streams_response['logStreams']:
            stream_name = stream['logStreamName']
            print(f"\nLog Stream: {stream_name}")
            print("-" * 70)
            
            try:
                events_response = logs.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    startFromHead=True,
                    limit=100
                )
                
                for event in events_response['events']:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', 
                                            time.localtime(event['timestamp']/1000))
                    message = event['message'].rstrip()
                    print(f"[{timestamp}] {message}")
                
                if not events_response['events']:
                    print("(No log events yet)")
                    
            except Exception as e:
                print(f"Error reading log stream: {e}")
    
    except logs.exceptions.ResourceNotFoundException:
        print(f"Log group {log_group} not found")
    except Exception as e:
        print(f"Error accessing logs: {e}")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    check_training_logs()
