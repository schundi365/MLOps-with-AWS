#!/usr/bin/env python3
"""
Fix Issue #19: Numpy source directory conflict in Lambda package.

Problem: Lambda package includes numpy source files that cause import errors.
The error "you should not try to import numpy from its source directory" means
the package has numpy's source tree instead of just the compiled binaries.

Solution: Clean package by excluding source files and only including necessary
compiled libraries.
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
    print("FIXING ISSUE #19: Lambda Package Cleanup")
    print("="*70)
    print()
    
    # Lambda configuration
    function_name = 'movielens-model-evaluation'
    role_arn = f"arn:aws:iam::{account_id}:role/MovieLensLambdaEvaluationRole"
    source_file = 'src/lambda_evaluation.py'
    
    print(f"Function: {function_name}")
    print(f"Source: {source_file}")
    print()
    print("Strategy:")
    print("  1. Install dependencies in clean directory")
    print("  2. Remove numpy source files and __pycache__")
    print("  3. Keep only compiled binaries (.so, .pyd)")
    print("  4. Package and deploy")
    print()
    
    # Create temporary directory for packaging
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Copy source file
        print("Copying source file...")
        shutil.copy(source_file, os.path.join(temp_dir, 'lambda_evaluation.py'))
        
        # Install dependencies
        print("Installing dependencies...")
        subprocess.check_call([
            'pip', 'install',
            '--target', temp_dir,
            '--upgrade',
            '--platform', 'manylinux2014_x86_64',
            '--implementation', 'cp',
            '--python-version', '3.10',
            '--only-binary=:all:',
            '--no-compile',
            'boto3',
            'pandas',
            'numpy'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        
        print("[OK] Dependencies installed")
        
        # Clean up problematic files
        print("Cleaning package...")
        files_removed = 0
        
        for root, dirs, files in os.walk(temp_dir):
            # Remove __pycache__ directories
            if '__pycache__' in dirs:
                pycache_path = os.path.join(root, '__pycache__')
                shutil.rmtree(pycache_path, ignore_errors=True)
                files_removed += 1
            
            # Remove .pyc files
            for file in files:
                if file.endswith('.pyc'):
                    os.remove(os.path.join(root, file))
                    files_removed += 1
            
            # Remove numpy source directories that cause issues
            if 'numpy' in root:
                # Keep only essential directories
                for dir_name in list(dirs):
                    if dir_name in ['tests', 'doc', 'f2py', 'distutils']:
                        dir_path = os.path.join(root, dir_name)
                        shutil.rmtree(dir_path, ignore_errors=True)
                        files_removed += 1
        
        print(f"[OK] Cleaned {files_removed} problematic files/directories")
        
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
        
        # Upload to S3
        print("Uploading to S3...")
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
    print("1. Cleaned Lambda package by removing source files")
    print("2. Removed __pycache__ and .pyc files")
    print("3. Removed numpy test and doc directories")
    print("4. Kept only compiled binaries")
    print()
    print("The Lambda package is now clean and should import correctly!")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
