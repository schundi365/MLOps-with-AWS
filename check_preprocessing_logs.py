"""
Check Preprocessing Logs

This script retrieves CloudWatch logs for the preprocessing job to diagnose failures.

Usage:
    python check_preprocessing_logs.py --job-name <preprocessing-job-name>
"""
import boto3
import argparse
from datetime import datetime, timedelta


def get_preprocessing_logs(job_name: str, region: str = 'us-east-1'):
    """Get CloudWatch logs for a preprocessing job"""
    
    logs_client = boto3.client('logs', region_name=region)
    
    print("\n" + "="*70)
    print("PREPROCESSING JOB LOGS")
    print("="*70 + "\n")
    
    print(f"Job Name: {job_name}")
    print(f"Region: {region}\n")
    
    # Log group for SageMaker processing jobs
    log_group = '/aws/sagemaker/ProcessingJobs'
    
    try:
        # Get log streams for this job
        print(f"[...] Searching for log streams in {log_group}")
        
        response = logs_client.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=job_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not response['logStreams']:
            print(f"[!] No log streams found for job: {job_name}")
            print("\nPossible reasons:")
            print("  1. Job hasn't started yet")
            print("  2. Job name is incorrect")
            print("  3. Logs haven't been created yet")
            return
        
        print(f"[OK] Found {len(response['logStreams'])} log stream(s)\n")
        
        # Get logs from each stream
        for stream in response['logStreams']:
            stream_name = stream['logStreamName']
            print("="*70)
            print(f"Log Stream: {stream_name}")
            print("="*70 + "\n")
            
            try:
                # Get log events
                log_response = logs_client.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    startFromHead=True,
                    limit=100
                )
                
                events = log_response['events']
                
                if not events:
                    print("[!] No log events in this stream\n")
                    continue
                
                print(f"[OK] Retrieved {len(events)} log events\n")
                
                # Print log events
                for event in events:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].rstrip()
                    print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
                
                print()
                
            except Exception as e:
                print(f"[X] Error reading log stream: {e}\n")
        
    except logs_client.exceptions.ResourceNotFoundException:
        print(f"[X] Log group not found: {log_group}")
        print("\nThis usually means:")
        print("  1. No processing jobs have run yet")
        print("  2. Logs are in a different region")
        
    except Exception as e:
        print(f"[X] Error retrieving logs: {e}")


def get_latest_preprocessing_job(region: str = 'us-east-1'):
    """Get the name of the latest preprocessing job"""
    
    sagemaker = boto3.client('sagemaker', region_name=region)
    
    try:
        response = sagemaker.list_processing_jobs(
            SortBy='CreationTime',
            SortOrder='Descending',
            MaxResults=1
        )
        
        if response['ProcessingJobSummaries']:
            job = response['ProcessingJobSummaries'][0]
            return job['ProcessingJobName']
        
    except Exception as e:
        print(f"[X] Error getting latest job: {e}")
    
    return None


def main():
    parser = argparse.ArgumentParser(
        description='Check CloudWatch logs for preprocessing job'
    )
    parser.add_argument(
        '--job-name',
        help='Preprocessing job name (e.g., movielens-preprocessing-20260119-223205-460)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--latest',
        action='store_true',
        help='Get logs for the latest preprocessing job'
    )
    
    args = parser.parse_args()
    
    job_name = args.job_name
    
    if args.latest or not job_name:
        print("[...] Finding latest preprocessing job...")
        job_name = get_latest_preprocessing_job(args.region)
        
        if not job_name:
            print("[X] No preprocessing jobs found")
            print("\nTry specifying the job name manually:")
            print("  python check_preprocessing_logs.py --job-name movielens-preprocessing-YYYYMMDD-HHMMSS-mmm")
            return 1
        
        print(f"[OK] Latest job: {job_name}\n")
    
    get_preprocessing_logs(job_name, args.region)
    
    print("="*70)
    print("TROUBLESHOOTING TIPS")
    print("="*70 + "\n")
    
    print("Common preprocessing errors:")
    print("  1. File not found: Check S3 paths in state machine")
    print("  2. Import error: Check if required packages are available")
    print("  3. Permission denied: Check IAM role permissions")
    print("  4. Out of memory: Increase instance size")
    print("\nTo view logs in AWS Console:")
    print(f"  https://console.aws.amazon.com/cloudwatch/home?region={args.region}#logsV2:log-groups/log-group/$252Faws$252Fsagemaker$252FProcessingJobs")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    import sys
    sys.exit(main() or 0)
