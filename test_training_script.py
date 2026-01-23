#!/usr/bin/env python3
"""
Test the training script for syntax errors and basic functionality.
"""

import sys
import subprocess
import tempfile
import os

def test_script_syntax():
    """Test if the training script has valid Python syntax."""
    
    print("\n" + "="*70)
    print("TESTING TRAINING SCRIPT")
    print("="*70)
    print()
    
    # Download the tarball from S3
    print("Downloading training script from S3...")
    import boto3
    s3 = boto3.client('s3', region_name='us-east-1')
    
    try:
        response = s3.get_object(
            Bucket='amzn-s3-movielens-327030626634',
            Key='code/sourcedir.tar.gz'
        )
        
        tarball_content = response['Body'].read()
        print(f"Downloaded {len(tarball_content)} bytes")
        
        # Extract and test
        import tarfile
        import io
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract tarball
            print("Extracting tarball...")
            with tarfile.open(fileobj=io.BytesIO(tarball_content), mode='r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Find train.py
            train_py = os.path.join(tmpdir, 'train.py')
            if not os.path.exists(train_py):
                print("[ERROR] train.py not found in tarball!")
                return False
            
            print(f"Found train.py at {train_py}")
            
            # Check syntax
            print("\nChecking Python syntax...")
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', train_py],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print("[ERROR] Syntax error in train.py!")
                print(result.stderr)
                return False
            
            print("[OK] Syntax is valid")
            
            # Try to import it
            print("\nTrying to import the script...")
            sys.path.insert(0, tmpdir)
            try:
                import train
                print("[OK] Script imports successfully")
                
                # Check if main classes exist
                if hasattr(train, 'CollaborativeFilteringModel'):
                    print("[OK] CollaborativeFilteringModel class found")
                else:
                    print("[ERROR] CollaborativeFilteringModel class not found!")
                    return False
                
                if hasattr(train, 'RatingsDataset'):
                    print("[OK] RatingsDataset class found")
                else:
                    print("[ERROR] RatingsDataset class not found!")
                    return False
                
                if hasattr(train, 'train'):
                    print("[OK] train function found")
                else:
                    print("[ERROR] train function not found!")
                    return False
                
                print("\n[SUCCESS] All checks passed!")
                return True
                
            except Exception as e:
                print(f"[ERROR] Failed to import: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_script_syntax()
    sys.exit(0 if success else 1)
