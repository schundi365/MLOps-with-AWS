#!/usr/bin/env python3
"""
Inspect model artifacts to verify inference code is included.
"""
import boto3
import tarfile
import tempfile
import os

def inspect_model_artifacts():
    """Download and inspect the latest model artifacts."""
    s3 = boto3.client('s3', region_name='us-east-1')
    
    # Latest model from Execution #25
    bucket = 'amzn-s3-movielens-327030626634'
    key = 'models/movielens-training-20260122-113429-368/output/model.tar.gz'
    
    print("\n" + "="*70)
    print("INSPECTING MODEL ARTIFACTS")
    print("="*70)
    print(f"\nBucket: {bucket}")
    print(f"Key: {key}")
    
    # Download to temp file
    tmp_path = os.path.join(tempfile.gettempdir(), 'model_inspect.tar.gz')
    print(f"\nDownloading to: {tmp_path}")
    
    # Remove if exists
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
    
    s3.download_file(bucket, key, tmp_path)
    print("Download complete")
    
    # Extract and list contents
    print("\n" + "="*70)
    print("MODEL ARCHIVE CONTENTS")
    print("="*70)
    
    with tarfile.open(tmp_path, 'r:gz') as tar:
        members = tar.getmembers()
        print(f"\nTotal files: {len(members)}\n")
        
        for member in members:
            size_kb = member.size / 1024
            print(f"  {member.name:<40} {size_kb:>10.2f} KB")
            
            # Check for code directory
            if member.name.startswith('code/'):
                print(f"    ^-- FOUND: Inference code file!")
        
        # Check specifically for required files
        print("\n" + "="*70)
        print("REQUIRED FILES CHECK")
        print("="*70)
        
        required_files = {
            'model.pth': False,
            'metadata.json': False,
            'code/inference.py': False,
            'code/model.py': False
        }
        
        for member in members:
            if member.name in required_files:
                required_files[member.name] = True
        
        for filename, found in required_files.items():
            status = "FOUND" if found else "MISSING"
            symbol = "+" if found else "X"
            print(f"  [{symbol}] {filename:<30} {status}")
        
        # Extract and show first few lines of inference.py if it exists
        if required_files['code/inference.py']:
            print("\n" + "="*70)
            print("INFERENCE.PY PREVIEW (first 20 lines)")
            print("="*70)
            
            inference_file = tar.extractfile('code/inference.py')
            if inference_file:
                lines = inference_file.read().decode('utf-8').split('\n')
                for i, line in enumerate(lines[:20], 1):
                    print(f"{i:3}: {line}")
    
    # Cleanup
    os.unlink(tmp_path)
    print("\n" + "="*70)

if __name__ == '__main__':
    inspect_model_artifacts()
