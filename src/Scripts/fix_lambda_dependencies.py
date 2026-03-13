#!/usr/bin/env python3
"""
Fix Issue #18: Missing pandas dependency in Lambda evaluation function.

Problem: Lambda function fails with "No module named 'pandas'" because
pandas wasn't included in the deployment package.

Solution: Redeploy Lambda with pandas included in dependencies.
"""

import boto3
import os
import zipfile
import tempfile
import shutil
import subprocess

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #18: Missing Lambda Dependencies")
    print("="*70)
    print()
    
    # Lambda configuration
    function_name = 'movielens-model-evaluation'
    role_arn = f"arn:aws:iam::{account_id}:role/MovieLensLambdaEvaluationRole"
    source_file = 'src/lambda_evaluation.py'
    
    print(f"Function: {function_name}")
    print(f"Source: {source_file}")
    print()
    print("Adding dependencies:")
    print("  - boto3 (AWS SDK)")
    print("  - pandas (data manipulation)")
    print("  - numpy (numerical operations)")
    print()
    
    # Create temporary directory for packaging
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Copy source file
        print("Copying source file...")
        shutil.copy(source_file, os.path.join(temp_dir, 'lambda_evaluation.py'))
        
        # Install dependencies
        print("Installing dependencies (this may take a minute)...")
        subprocess.check_call([
            'pip', 'install',
            '--target', temp_dir,
            '--upgrade',
            '--platform', 'manylinux2014_x86_64',
            '--only-binary=:all:',
            'boto3',
            'pandas',
            'numpy'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        
        print("[OK] Dependencies installed")
        
        # Create zip file
        print("Creating deployment package...")
        zip_path = os.path.join(tempfile.gettempdir(), f'{function_name}.zip')
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
        
        zip_size = os.path.getsize(zip_path)
        print(f"[OK] Package created: {zip_size:,} bytes")
        
        # Check if package is too large for direct upload (50MB limit)
        if zip_size > 50 * 1024 * 1024:
            print("Package is large, uploading to S3 first...")
            
            # Upload to S3
            s3_client = boto3.client('s3', region_name=region)
            s3_key = f'lambda/{function_name}.zip'
            
            with open(zip_path, 'rb') as f:
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=s3_key,
                    Body=f
                )
            
            print(f"[OK] Uploaded to s3://{bucket_name}/{s3_key}")
            
            # Deploy to Lambda from S3
            print("Deploying to Lambda from S3...")
            lambda_client = boto3.client('lambda', region_name=region)
            
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                S3Bucket=bucket_name,
                S3Key=s3_key
            )
        else:
            # Deploy to Lambda directly
            print("Deploying to Lambda...")
            lambda_client = boto3.client('lambda', region_name=region)
            
            with open(zip_path, 'rb') as f:
                zip_content = f.read()
            
            # Update function code
            response = lambda_client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_content
            )
        
        print("[OK] Lambda function updated")
        
        # Wait for update to complete
        print("Waiting for update to complete...")
        waiter = lambda_client.get_waiter('function_updated')
        waiter.wait(
            FunctionName=function_name,
            WaiterConfig={'Delay': 2, 'MaxAttempts': 30}
        )
        
        print("[OK] Update complete")
        
        # Clean up
        os.remove(zip_path)
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    print()
    print("="*70)
    print("FIX APPLIED")
    print("="*70)
    print()
    print("Changes made:")
    print("1. Added pandas to Lambda deployment package")
    print("2. Added numpy to Lambda deployment package")
    print("3. Updated boto3 to latest version")
    print()
    print("The Lambda function now has all required dependencies!")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
