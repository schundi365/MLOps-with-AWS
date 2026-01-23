"""
Fix the sourcedir.tar.gz to include inference.py and model.py.

The training script tries to copy inference.py and model.py into the model
artifacts, but these files are not in the sourcedir.tar.gz that gets extracted
to /opt/ml/code/ during training.

This script recreates sourcedir.tar.gz with all necessary files.
"""

import boto3
import tarfile
import os

def fix_sourcedir():
    """Recreate sourcedir.tar.gz with all necessary files."""
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING SOURCEDIR.TAR.GZ")
    print("="*70 + "\n")
    
    print("Problem: sourcedir.tar.gz only contains train.py")
    print("Solution: Recreate it with train.py, inference.py, and model.py")
    print()
    
    # Create new tarball
    print("Step 1: Creating new sourcedir.tar.gz...")
    
    files_to_include = [
        ('src/train.py', 'train.py'),
        ('src/inference.py', 'inference.py'),
        ('src/model.py', 'model.py'),
    ]
    
    with tarfile.open('sourcedir.tar.gz', 'w:gz') as tar:
        for src_path, arcname in files_to_include:
            if os.path.exists(src_path):
                tar.add(src_path, arcname=arcname)
                print(f"  ✓ Added {arcname} from {src_path}")
            else:
                print(f"  ✗ ERROR: {src_path} not found!")
                return False
    
    print()
    
    # Upload to S3
    print("Step 2: Uploading to S3...")
    
    with open('sourcedir.tar.gz', 'rb') as f:
        s3_client.upload_fileobj(
            f,
            bucket_name,
            'code/sourcedir.tar.gz'
        )
    
    print(f"  ✓ Uploaded to s3://{bucket_name}/code/sourcedir.tar.gz")
    print()
    
    # Clean up local file
    os.remove('sourcedir.tar.gz')
    
    # Verify
    print("Step 3: Verifying upload...")
    
    import io
    obj = s3_client.get_object(Bucket=bucket_name, Key='code/sourcedir.tar.gz')
    tar = tarfile.open(fileobj=io.BytesIO(obj['Body'].read()))
    
    print("  Files in uploaded tarball:")
    for member in tar.getmembers():
        print(f"    - {member.name}")
    
    tar.close()
    print()
    
    print("="*70)
    print("FIX COMPLETE")
    print("="*70)
    print()
    print("The sourcedir.tar.gz now contains:")
    print("  - train.py (training script)")
    print("  - inference.py (custom inference handler)")
    print("  - model.py (model architecture)")
    print()
    print("NEXT STEPS:")
    print("1. Start a new pipeline execution")
    print("2. The training script will now be able to copy inference.py and")
    print("   model.py into the model artifacts")
    print("3. The endpoint will use the custom inference handler")
    print()
    print("To start a new execution:")
    print("  python start_pipeline_with_correct_input.py")
    print()
    
    return True

if __name__ == '__main__':
    success = fix_sourcedir()
    if not success:
        print("\nFix failed. Please check that all source files exist.")
        exit(1)
