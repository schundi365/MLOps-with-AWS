"""
Check detailed training error for the current execution.
"""

import boto3
import time

def check_training_error():
    """Get detailed training error from CloudWatch logs."""
    
    sagemaker = boto3.client('sagemaker', region_name='us-east-1')
    logs = boto3.client('logs', region_name='us-east-1')
    
    print("\n" + "="*70)
    print("TRAINING JOB ERROR DETAILS")
    print("="*70 + "\n")
    
    training_job_name = 'movielens-training-20260123-114011'
    
    # Get training job details
    try:
        response = sagemaker.describe_training_job(TrainingJobName=training_job_name)
        
        print(f"Training Job: {training_job_name}")
        print(f"Status: {response['TrainingJobStatus']}")
        
        if 'SecondaryStatus' in response:
            print(f"Secondary Status: {response['SecondaryStatus']}")
        
        if 'FailureReason' in response:
            print(f"\nFailure Reason:")
            print("-" * 70)
            print(response['FailureReason'])
            print("-" * 70)
        
        print()
        
    except Exception as e:
        print(f"Error getting training job details: {e}\n")
        return
    
    # Get CloudWatch logs
    log_group = "/aws/sagemaker/TrainingJobs"
    
    print("CloudWatch Logs (Last 100 lines):")
    print("="*70)
    
    try:
        # List log streams
        streams_response = logs.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=training_job_name,
            descending=True,
            limit=5
        )
        
        if not streams_response.get('logStreams'):
            print("No log streams found")
            return
        
        # Get logs from all streams
        for stream in streams_response['logStreams']:
            stream_name = stream['logStreamName']
            print(f"\n--- Log Stream: {stream_name} ---\n")
            
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
                
            except Exception as e:
                print(f"Error reading log stream: {e}")
    
    except Exception as e:
        print(f"Error accessing logs: {e}")
    
    print("\n" + "="*70)

if __name__ == '__main__':
    check_training_error()
