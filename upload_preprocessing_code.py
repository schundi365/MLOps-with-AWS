"""
Upload Preprocessing Code to S3

This script uploads the preprocessing.py script to S3 so it can be used
by SageMaker processing jobs.

Usage:
    python upload_preprocessing_code.py --bucket amzn-s3-movielens-327030626634
"""

import boto3
import argparse
import os
from botocore.exceptions import ClientError


def upload_preprocessing_code(bucket_name: str, region: str = 'us-east-1'):
    """
    Upload preprocessing code to S3
    
    Args:
        bucket_name: S3 bucket name
        region: AWS region
        
    Returns:
        True if successful
    """
    s3 = boto3.client('s3', region_name=region)
    
    print("\n" + "="*70)
    print("UPLOADING PREPROCESSING CODE TO S3")
    print("="*70 + "\n")
    
    # Check if preprocessing.py exists
    preprocessing_file = 'src/preprocessing.py'
    
    if not os.path.exists(preprocessing_file):
        print(f"[X] File not found: {preprocessing_file}")
        print("    Make sure you're running this from the project root directory")
        return False
    
    try:
        # Upload preprocessing.py to S3
        s3_key = 'code/preprocessing.py'
        
        print(f"[...] Uploading {preprocessing_file} to s3://{bucket_name}/{s3_key}")
        
        with open(preprocessing_file, 'rb') as f:
            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=f,
                ContentType='text/x-python'
            )
        
        print(f"[OK] Successfully uploaded preprocessing code")
        print(f"\nS3 URI: s3://{bucket_name}/{s3_key}")
        
        # Verify upload
        response = s3.head_object(Bucket=bucket_name, Key=s3_key)
        file_size = response['ContentLength']
        print(f"File size: {file_size} bytes")
        
        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70 + "\n")
        
        print("The preprocessing code has been uploaded to S3.")
        print("Now you need to update the Step Functions state machine to use it.")
        print("\nRun:")
        print(f"  python fix_preprocessing_input.py --bucket {bucket_name}")
        
        print("\n" + "="*70 + "\n")
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'NoSuchBucket':
            print(f"[X] Bucket does not exist: {bucket_name}")
            return False
        else:
            print(f"[X] Error uploading file: {e}")
            return False
    except Exception as e:
        print(f"[X] Unexpected error: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Upload preprocessing code to S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Upload preprocessing code
  python upload_preprocessing_code.py --bucket amzn-s3-movielens-327030626634
  
  # Upload to different region
  python upload_preprocessing_code.py --bucket my-bucket --region us-west-2
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
    
    success = upload_preprocessing_code(args.bucket, args.region)
    
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

