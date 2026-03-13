#!/usr/bin/env python3
"""
Check what's in the training code tarball on S3.
"""
import boto3
import tarfile
import tempfile
import os

def check_training_code():
    """Download and inspect the training code tarball."""
    s3 = boto3.client('s3', region_name='us-east-1')
    
    bucket = 'amzn-s3-movielens-327030626634'
    key = 'training-code/sourcedir.tar.gz'
    
    print("\n" + "="*70)
    print("CHECKING TRAINING CODE TARBALL")
    print("="*70)
    print(f"\nBucket: {bucket}")
    print(f"Key: {key}")
    
    # Download to temp file
    tmp_path = os.path.join(tempfile.gettempdir(), 'training_code_inspect.tar.gz')
    print(f"\nDownloading to: {tmp_path}")
    
    # Remove if exists
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
    
    s3.download_file(bucket, key, tmp_path)
    print("Download complete")
    
    # Extract and list contents
    print("\n" + "="*70)
    print("TRAINING CODE ARCHIVE CONTENTS")
    print("="*70)
    
    with tarfile.open(tmp_path, 'r:gz') as tar:
        members = tar.getmembers()
        print(f"\nTotal files: {len(members)}\n")
        
        for member in members:
            size_kb = member.size / 1024
            print(f"  {member.name:<40} {size_kb:>10.2f} KB")
        
        # Check specifically for required files
        print("\n" + "="*70)
        print("REQUIRED FILES CHECK")
        print("="*70)
        
        required_files = {
            'train.py': False,
            'model.py': False,
            'inference.py': False,
            'preprocessing.py': False
        }
        
        for member in members:
            # Handle both with and without directory prefix
            basename = os.path.basename(member.name)
            if basename in required_files:
                required_files[basename] = True
        
        for filename, found in required_files.items():
            status = "FOUND" if found else "MISSING"
            symbol = "+" if found else "X"
            print(f"  [{symbol}] {filename:<30} {status}")
    
    # Cleanup
    os.unlink(tmp_path)
    print("\n" + "="*70)

if __name__ == '__main__':
    check_training_code()
