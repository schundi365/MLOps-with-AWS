"""
Check S3 Progress - Monitor Pipeline via S3 File Creation

This script checks S3 for files created by the pipeline to infer progress.
Works without Step Functions or SageMaker permissions.

Usage:
    python check_s3_progress.py --bucket amzn-s3-movielens-327030626634
"""

import boto3
import argparse
from datetime import datetime
from botocore.exceptions import ClientError


def check_s3_progress(bucket_name: str, region: str = 'us-east-1'):
    """
    Check pipeline progress by looking at S3 files
    
    Args:
        bucket_name: S3 bucket name
        region: AWS region
    """
    s3 = boto3.client('s3', region_name=region)
    
    print("\n" + "="*70)
    print("PIPELINE PROGRESS CHECK (via S3)")
    print("="*70 + "\n")
    
    print(f"Bucket: {bucket_name}")
    print(f"Region: {region}")
    print(f"Check Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")
    
    # Define what to check
    checks = [
        {
            "name": "Raw Data",
            "prefix": "raw-data/",
            "stage": "Data Upload",
            "expected": "4 files (u.data, u.item, u.user, u.genre)"
        },
        {
            "name": "Processed Data",
            "prefix": "processed-data/",
            "stage": "Preprocessing",
            "expected": "train/, validation/, test/ folders"
        },
        {
            "name": "Model Artifacts",
            "prefix": "models/",
            "stage": "Training",
            "expected": "model.tar.gz and training metrics"
        },
        {
            "name": "Evaluation Results",
            "prefix": "outputs/evaluation/",
            "stage": "Evaluation",
            "expected": "metrics.json with RMSE, MAE, etc."
        },
        {
            "name": "Deployment Outputs",
            "prefix": "outputs/",
            "stage": "Deployment",
            "expected": "endpoint configuration and status"
        }
    ]
    
    results = []
    
    for check in checks:
        try:
            response = s3.list_objects_v2(
                Bucket=bucket_name,
                Prefix=check['prefix'],
                MaxKeys=10
            )
            
            if 'Contents' in response and len(response['Contents']) > 0:
                file_count = response['KeyCount']
                latest_file = max(response['Contents'], key=lambda x: x['LastModified'])
                latest_time = latest_file['LastModified'].strftime('%Y-%m-%d %H:%M:%S UTC')
                
                results.append({
                    'name': check['name'],
                    'stage': check['stage'],
                    'status': 'COMPLETE',
                    'files': file_count,
                    'latest': latest_time
                })
                
                print(f"[OK] {check['name']}")
                print(f"     Stage: {check['stage']}")
                print(f"     Files: {file_count}")
                print(f"     Latest: {latest_time}")
                print()
            else:
                results.append({
                    'name': check['name'],
                    'stage': check['stage'],
                    'status': 'PENDING',
                    'files': 0,
                    'latest': 'N/A'
                })
                
                print(f"[ ] {check['name']}")
                print(f"     Stage: {check['stage']}")
                print(f"     Status: Not started or in progress")
                print()
                
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchBucket':
                print(f"[X] Bucket {bucket_name} does not exist!")
                return False
            else:
                print(f"[X] Error checking {check['name']}: {e}")
                results.append({
                    'name': check['name'],
                    'stage': check['stage'],
                    'status': 'ERROR',
                    'files': 0,
                    'latest': 'N/A'
                })
    
    # Determine current stage
    print("="*70)
    print("PIPELINE STAGE INFERENCE")
    print("="*70 + "\n")
    
    completed_stages = [r for r in results if r['status'] == 'COMPLETE']
    
    if len(completed_stages) == 0:
        print("[!] Pipeline has not started or is in very early stages")
        print("    Expected: Raw data should be uploaded first")
    elif len(completed_stages) == 1:
        print("[...] Pipeline is in PREPROCESSING stage")
        print("      Raw data uploaded, waiting for processed data")
        print("      Expected duration: 5-10 minutes")
    elif len(completed_stages) == 2:
        print("[...] Pipeline is in TRAINING stage")
        print("      Data preprocessed, model training in progress")
        print("      Expected duration: 30-45 minutes")
        print("      This is the longest stage - be patient!")
    elif len(completed_stages) == 3:
        print("[...] Pipeline is in EVALUATION stage")
        print("      Model trained, evaluation in progress")
        print("      Expected duration: 2-5 minutes")
    elif len(completed_stages) == 4:
        print("[...] Pipeline is in DEPLOYMENT stage")
        print("      Model evaluated, deploying to endpoint")
        print("      Expected duration: 5-10 minutes")
    elif len(completed_stages) == 5:
        print("[OK] Pipeline appears to be COMPLETE!")
        print("     All stages have created output files")
        print("\n     Next steps:")
        print("     1. Verify deployment: python verify_deployment.py")
        print("     2. Test endpoint: python test_inference.py")
        print("     3. Check CloudWatch dashboard")
    
    print("\n" + "="*70)
    print("MONITORING TIPS")
    print("="*70 + "\n")
    
    print("1. Run this script periodically to check progress:")
    print(f"   python check_s3_progress.py --bucket {bucket_name}")
    
    print("\n2. For real-time monitoring, use AWS Console:")
    print("   https://console.aws.amazon.com/states/home?region=us-east-1")
    
    print("\n3. Check specific S3 folders:")
    print(f"   aws s3 ls s3://{bucket_name}/processed-data/")
    print(f"   aws s3 ls s3://{bucket_name}/models/")
    
    print("\n4. After completion, verify deployment:")
    print(f"   python verify_deployment.py --bucket-name {bucket_name}")
    
    print("\n" + "="*70 + "\n")
    
    return True


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Check pipeline progress via S3 file creation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check progress
  python check_s3_progress.py --bucket amzn-s3-movielens-327030626634
  
  # Check in different region
  python check_s3_progress.py --bucket my-bucket --region us-west-2
  
This script works without Step Functions or SageMaker permissions.
It infers pipeline progress by checking which files exist in S3.
        """
    )
    
    parser.add_argument(
        '--bucket',
        required=True,
        help='S3 bucket name'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    success = check_s3_progress(args.bucket, args.region)
    
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

