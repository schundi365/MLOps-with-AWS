"""
Monitor the execution with fixed hyperparameter names.
"""

import boto3
import time
from datetime import datetime

def monitor_execution():
    """Monitor the current pipeline execution."""
    
    sfn = boto3.client('stepfunctions', region_name='us-east-1')
    sagemaker = boto3.client('sagemaker', region_name='us-east-1')
    logs = boto3.client('logs', region_name='us-east-1')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    execution_name = 'execution-20260123-114011-hyphen-fix'
    execution_arn = f"arn:aws:states:us-east-1:{account_id}:execution:MovieLensMLPipeline:{execution_name}"
    
    print("\n" + "="*70)
    print("MONITORING PIPELINE EXECUTION")
    print("="*70 + "\n")
    
    print(f"Execution: {execution_name}")
    print(f"ARN: {execution_arn}")
    print()
    
    try:
        response = sfn.describe_execution(executionArn=execution_arn)
        
        print(f"Status: {response['status']}")
        print(f"Start Time: {response['startDate']}")
        
        if 'stopDate' in response:
            print(f"Stop Time: {response['stopDate']}")
            duration = (response['stopDate'] - response['startDate']).total_seconds()
            print(f"Duration: {duration:.0f} seconds ({duration/60:.1f} minutes)")
        
        print()
        
        # Get execution history to see current step
        history = sfn.get_execution_history(
            executionArn=execution_arn,
            maxResults=100,
            reverseOrder=True
        )
        
        print("Recent Events:")
        print("-" * 70)
        
        for event in history['events'][:10]:
            timestamp = event['timestamp'].strftime('%H:%M:%S')
            event_type = event['type']
            
            # Extract relevant details based on event type
            details = ""
            if 'stateEnteredEventDetails' in event:
                details = f" - {event['stateEnteredEventDetails']['name']}"
            elif 'stateExitedEventDetails' in event:
                details = f" - {event['stateExitedEventDetails']['name']}"
            elif 'taskFailedEventDetails' in event:
                details = f" - ERROR: {event['taskFailedEventDetails'].get('error', 'Unknown')}"
            
            print(f"[{timestamp}] {event_type}{details}")
        
        print()
        
        # Check training job if in progress
        training_job_name = 'movielens-training-20260123-114011'
        
        try:
            training_response = sagemaker.describe_training_job(
                TrainingJobName=training_job_name
            )
            
            print("="*70)
            print("TRAINING JOB STATUS")
            print("="*70)
            print()
            print(f"Job Name: {training_job_name}")
            print(f"Status: {training_response['TrainingJobStatus']}")
            
            if 'SecondaryStatus' in training_response:
                print(f"Secondary Status: {training_response['SecondaryStatus']}")
            
            if 'FailureReason' in training_response:
                print(f"Failure Reason: {training_response['FailureReason']}")
            
            # Show training metrics if available
            if 'FinalMetricDataList' in training_response:
                print("\nMetrics:")
                for metric in training_response['FinalMetricDataList']:
                    print(f"  {metric['MetricName']}: {metric['Value']:.4f}")
            
            print()
            
            # Get recent training logs
            print("Recent Training Logs:")
            print("-" * 70)
            
            log_group = "/aws/sagemaker/TrainingJobs"
            
            try:
                streams_response = logs.describe_log_streams(
                    logGroupName=log_group,
                    logStreamNamePrefix=training_job_name,
                    descending=True,
                    limit=1
                )
                
                if streams_response.get('logStreams'):
                    stream_name = streams_response['logStreams'][0]['logStreamName']
                    
                    events_response = logs.get_log_events(
                        logGroupName=log_group,
                        logStreamName=stream_name,
                        startFromHead=False,
                        limit=20
                    )
                    
                    for event in events_response['events']:
                        timestamp = time.strftime('%H:%M:%S', 
                                                time.localtime(event['timestamp']/1000))
                        message = event['message'].rstrip()
                        print(f"[{timestamp}] {message}")
                else:
                    print("(No log streams available yet)")
                    
            except logs.exceptions.ResourceNotFoundException:
                print("(Log group not found - training may not have started)")
            except Exception as e:
                print(f"(Error reading logs: {e})")
            
            print()
            
        except sagemaker.exceptions.ClientError as e:
            if 'Could not find' in str(e):
                print("Training job not started yet")
            else:
                print(f"Error checking training job: {e}")
        
        print("="*70)
        print("KEY THINGS TO VERIFY")
        print("="*70)
        print()
        print("✓ Training arguments should now be parsed correctly")
        print("  Look for: 'Namespace(batch_size=256, learning_rate=0.001, ...)'")
        print("  NOT: 'error: unrecognized arguments'")
        print()
        print("✓ Inference files should be copied to model artifacts")
        print("  Look for: 'Copied inference.py from ... to ...'")
        print("  Look for: 'Copied model.py from ... to ...'")
        print()
        print("✓ Training should complete successfully")
        print("  Look for: 'Training script completed successfully'")
        print()
        
    except Exception as e:
        print(f"Error monitoring execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    monitor_execution()
