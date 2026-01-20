"""
Check Training Job Error

Usage:
    python check_training_error.py --bucket <bucket-name>
"""
import boto3
import json
import argparse
from datetime import datetime


def get_latest_training_job(region: str = 'us-east-1'):
    """Get the latest training job"""
    
    sagemaker = boto3.client('sagemaker', region_name=region)
    
    try:
        response = sagemaker.list_training_jobs(
            SortBy='CreationTime',
            SortOrder='Descending',
            MaxResults=1
        )
        
        if response['TrainingJobSummaries']:
            return response['TrainingJobSummaries'][0]
        
    except Exception as e:
        print(f"[X] Error: {e}")
    
    return None


def check_training_job(job_name: str, region: str = 'us-east-1'):
    """Check training job details"""
    
    sagemaker = boto3.client('sagemaker', region_name=region)
    
    print("\n" + "="*70)
    print("TRAINING JOB DETAILS")
    print("="*70 + "\n")
    
    try:
        response = sagemaker.describe_training_job(TrainingJobName=job_name)
        
        print(f"Job Name: {job_name}")
        print(f"Status: {response['TrainingJobStatus']}")
        print(f"Created: {response['CreationTime']}")
        
        if 'FailureReason' in response:
            print(f"\n{'='*70}")
            print("FAILURE REASON")
            print("="*70)
            print(f"\n{response['FailureReason']}\n")
        
        # Check algorithm error
        if 'AlgorithmSpecification' in response:
            algo = response['AlgorithmSpecification']
            print(f"\nAlgorithm:")
            print(f"  Training Image: {algo.get('TrainingImage', 'N/A')}")
            print(f"  Training Input Mode: {algo.get('TrainingInputMode', 'N/A')}")
        
        # Check input data
        if 'InputDataConfig' in response:
            print(f"\nInput Data:")
            for channel in response['InputDataConfig']:
                channel_name = channel['ChannelName']
                data_source = channel['DataSource']['S3DataSource']
                s3_uri = data_source['S3Uri']
                print(f"  {channel_name}: {s3_uri}")
        
        # Check output
        if 'OutputDataConfig' in response:
            output = response['OutputDataConfig']
            print(f"\nOutput:")
            print(f"  S3 Output Path: {output['S3OutputPath']}")
        
        # Check resource config
        if 'ResourceConfig' in response:
            resource = response['ResourceConfig']
            print(f"\nResources:")
            print(f"  Instance Type: {resource['InstanceType']}")
            print(f"  Instance Count: {resource['InstanceCount']}")
            print(f"  Volume Size: {resource['VolumeSizeInGB']} GB")
        
        return response
        
    except Exception as e:
        print(f"[X] Error: {e}")
        return None


def check_cloudwatch_logs(job_name: str, region: str = 'us-east-1'):
    """Check CloudWatch logs for training job"""
    
    logs = boto3.client('logs', region_name=region)
    
    log_group = '/aws/sagemaker/TrainingJobs'
    
    print(f"\n{'='*70}")
    print("CLOUDWATCH LOGS")
    print("="*70 + "\n")
    
    try:
        # Get log streams
        response = logs.describe_log_streams(
            logGroupName=log_group,
            logStreamNamePrefix=job_name,
            orderBy='LastEventTime',
            descending=True,
            limit=5
        )
        
        if not response['logStreams']:
            print(f"[!] No log streams found for job: {job_name}")
            return
        
        print(f"[OK] Found {len(response['logStreams'])} log stream(s)\n")
        
        # Get logs from the first stream (usually the main one)
        for stream in response['logStreams'][:2]:  # Check first 2 streams
            stream_name = stream['logStreamName']
            print(f"{'='*70}")
            print(f"Log Stream: {stream_name}")
            print("="*70 + "\n")
            
            try:
                log_response = logs.get_log_events(
                    logGroupName=log_group,
                    logStreamName=stream_name,
                    startFromHead=False,  # Get most recent
                    limit=50
                )
                
                events = log_response['events']
                
                if not events:
                    print("[!] No log events\n")
                    continue
                
                # Print last 50 events
                for event in events:
                    timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                    message = event['message'].rstrip()
                    print(f"[{timestamp.strftime('%H:%M:%S')}] {message}")
                
                print()
                
            except Exception as e:
                print(f"[X] Error reading logs: {e}\n")
        
    except logs.exceptions.ResourceNotFoundException:
        print(f"[!] Log group not found: {log_group}")
    except Exception as e:
        print(f"[X] Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Check training job error details'
    )
    parser.add_argument(
        '--job-name',
        help='Training job name'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    job_name = args.job_name
    
    if not job_name:
        print("[...] Finding latest training job...")
        job_summary = get_latest_training_job(args.region)
        
        if not job_summary:
            print("[X] No training jobs found")
            return 1
        
        job_name = job_summary['TrainingJobName']
        print(f"[OK] Latest job: {job_name}\n")
    
    # Check job details
    job_details = check_training_job(job_name, args.region)
    
    if not job_details:
        return 1
    
    # Check CloudWatch logs
    check_cloudwatch_logs(job_name, args.region)
    
    print("="*70)
    print("TROUBLESHOOTING")
    print("="*70 + "\n")
    
    print("Common training errors:")
    print("  1. AttributeError: Check train.py for None values")
    print("  2. FileNotFoundError: Verify S3 paths")
    print("  3. ImportError: Check requirements.txt")
    print("  4. CUDA errors: Check instance type")
    print("\nView logs in AWS Console:")
    print(f"  https://console.aws.amazon.com/cloudwatch/home?region={args.region}#logsV2:log-groups/log-group/$252Faws$252Fsagemaker$252FTrainingJobs")
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    import sys
    sys.exit(main() or 0)
