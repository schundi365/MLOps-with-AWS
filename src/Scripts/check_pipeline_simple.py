"""
Simple pipeline status checker that doesn't require Step Functions permissions
Checks S3, Lambda logs, and SageMaker jobs instead
"""
import boto3
from datetime import datetime, timedelta

def check_s3_progress(bucket_name):
    """Check S3 for signs of pipeline progress"""
    print("\n=== Checking S3 Bucket Progress ===")
    s3 = boto3.client('s3', region_name='us-east-1')
    
    prefixes = [
        'raw-data/',
        'processed-data/',
        'models/',
        'outputs/',
        'monitoring/'
    ]
    
    for prefix in prefixes:
        try:
            response = s3.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=10
            )
            
            if 'Contents' in response:
                # Filter out directory markers
                files = [obj for obj in response['Contents'] 
                        if not obj['Key'].endswith('/')]
                
                if files:
                    latest = max(files, key=lambda x: x['LastModified'])
                    print(f"[OK] {prefix:20s} - {len(files)} files, "
                          f"latest: {latest['LastModified'].strftime('%H:%M:%S')}")
                else:
                    print(f"[--] {prefix:20s} - Empty")
            else:
                print(f"[--] {prefix:20s} - Empty")
        except Exception as e:
            print(f"[X] {prefix:20s} - Error: {e}")

def check_lambda_logs():
    """Check Lambda function logs for recent activity"""
    print("\n=== Checking Lambda Function Activity ===")
    logs = boto3.client('logs', region_name='us-east-1')
    
    functions = [
        '/aws/lambda/movielens-model-evaluation',
        '/aws/lambda/movielens-monitoring-setup'
    ]
    
    for log_group in functions:
        try:
            # Get recent log streams
            response = logs.describe_log_streams(
                logGroupName=log_group,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )
            
            if response['logStreams']:
                stream = response['logStreams'][0]
                last_event = datetime.fromtimestamp(
                    stream['lastEventTimestamp'] / 1000
                )
                time_ago = datetime.now() - last_event
                
                if time_ago < timedelta(hours=1):
                    status = "[ACTIVE]"
                else:
                    status = "[IDLE]"
                
                print(f"{status} {log_group.split('/')[-1]:30s} - "
                      f"Last activity: {time_ago.seconds // 60} min ago")
            else:
                print(f"[--] {log_group.split('/')[-1]:30s} - No logs yet")
        except logs.exceptions.ResourceNotFoundException:
            print(f"[--] {log_group.split('/')[-1]:30s} - No logs yet")
        except Exception as e:
            print(f"[X] {log_group.split('/')[-1]:30s} - Error: {e}")

def check_sagemaker_jobs():
    """Check for recent SageMaker training and endpoint jobs"""
    print("\n=== Checking SageMaker Activity ===")
    sagemaker = boto3.client('sagemaker', region_name='us-east-1')
    
    # Check training jobs
    try:
        response = sagemaker.list_training_jobs(
            SortBy='CreationTime',
            SortOrder='Descending',
            MaxResults=5
        )
        
        if response['TrainingJobSummaries']:
            print("\nRecent Training Jobs:")
            for job in response['TrainingJobSummaries']:
                if 'movielens' in job['TrainingJobName'].lower():
                    status_icon = {
                        'InProgress': '[RUNNING]',
                        'Completed': '[OK]',
                        'Failed': '[FAILED]',
                        'Stopped': '[STOPPED]'
                    }.get(job['TrainingJobStatus'], '[?]')
                    
                    print(f"  {status_icon} {job['TrainingJobName']}")
                    print(f"       Status: {job['TrainingJobStatus']}")
                    print(f"       Created: {job['CreationTime'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("\n[--] No training jobs found")
    except Exception as e:
        print(f"\n[X] Error checking training jobs: {e}")
    
    # Check endpoints
    try:
        response = sagemaker.list_endpoints(
            SortBy='CreationTime',
            SortOrder='Descending',
            MaxResults=5
        )
        
        if response['Endpoints']:
            print("\nRecent Endpoints:")
            for endpoint in response['Endpoints']:
                if 'movielens' in endpoint['EndpointName'].lower():
                    status_icon = {
                        'InService': '[OK]',
                        'Creating': '[CREATING]',
                        'Updating': '[UPDATING]',
                        'Failed': '[FAILED]'
                    }.get(endpoint['EndpointStatus'], '[?]')
                    
                    print(f"  {status_icon} {endpoint['EndpointName']}")
                    print(f"       Status: {endpoint['EndpointStatus']}")
                    print(f"       Created: {endpoint['CreationTime'].strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("\n[--] No endpoints found")
    except Exception as e:
        print(f"\n[X] Error checking endpoints: {e}")

def main():
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("MovieLens Pipeline Status Check")
    print("="*70)
    
    check_s3_progress(bucket_name)
    check_lambda_logs()
    check_sagemaker_jobs()
    
    print("\n" + "="*70)
    print("Status Check Complete")
    print("="*70)
    print("\nFor detailed monitoring, use AWS Console:")
    print("  Step Functions: https://console.aws.amazon.com/states/home?region=us-east-1")
    print("  CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups")
    print("  SageMaker: https://console.aws.amazon.com/sagemaker/home?region=us-east-1")
    print("\nOr add permissions:")
    print("  python add_user_permissions.py")
    print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()
