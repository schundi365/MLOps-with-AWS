#!/usr/bin/env python3
"""Check if model artifacts exist in S3 for recent training jobs."""

import boto3
from datetime import datetime

def main():
    region = 'us-east-1'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    s3_client = boto3.client('s3', region_name=region)
    sagemaker_client = boto3.client('sagemaker', region_name=region)
    
    print("\n" + "="*70)
    print("CHECKING MODEL ARTIFACTS")
    print("="*70)
    print()
    
    # List recent training jobs
    print("Recent training jobs:")
    print()
    
    response = sagemaker_client.list_training_jobs(
        MaxResults=5,
        SortBy='CreationTime',
        SortOrder='Descending'
    )
    
    for job in response['TrainingJobSummaries']:
        job_name = job['TrainingJobName']
        status = job['TrainingJobStatus']
        creation_time = job['CreationTime']
        
        print(f"Job: {job_name}")
        print(f"  Status: {status}")
        print(f"  Created: {creation_time}")
        
        # Get job details
        job_details = sagemaker_client.describe_training_job(
            TrainingJobName=job_name
        )
        
        if 'ModelArtifacts' in job_details:
            model_data_url = job_details['ModelArtifacts'].get('S3ModelArtifacts', 'N/A')
            print(f"  Model URL: {model_data_url}")
            
            # Check if file exists
            if model_data_url != 'N/A' and model_data_url.startswith('s3://'):
                # Parse S3 URL
                parts = model_data_url.replace('s3://', '').split('/', 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ''
                
                try:
                    head_response = s3_client.head_object(Bucket=bucket, Key=key)
                    size_mb = head_response['ContentLength'] / (1024 * 1024)
                    print(f"  File exists: YES ({size_mb:.2f} MB)")
                except:
                    print(f"  File exists: NO")
        
        if 'FailureReason' in job_details:
            print(f"  Failure Reason: {job_details['FailureReason']}")
        
        print()
    
    print("="*70)

if __name__ == "__main__":
    main()
