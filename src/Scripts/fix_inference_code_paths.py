#!/usr/bin/env python3
"""
Fix Issue #26: Inference code not being copied due to incorrect paths.

The problem: In SageMaker training containers, the source code is extracted to
/opt/ml/code/, not to the same directory as train.py. The script was looking for
inference.py and model.py in the wrong location.

Solution: Update train.py to look for inference files in /opt/ml/code/ directory.
"""
import boto3
import tarfile
import tempfile
import os

def fix_training_script():
    """Fix the save_model function to use correct paths in SageMaker."""
    
    print("\n" + "="*70)
    print("ISSUE #26: FIXING INFERENCE CODE PATHS")
    print("="*70)
    
    # Read current train.py
    with open('src/train.py', 'r') as f:
        content = f.read()
    
    # Find and replace the inference code copying section
    old_code = '''    # Copy inference.py
    src_dir = os.path.dirname(os.path.abspath(__file__))
    inference_src = os.path.join(src_dir, 'inference.py')
    inference_dst = os.path.join(code_dir, 'inference.py')
    if os.path.exists(inference_src):
        shutil.copy2(inference_src, inference_dst)
        logger.info(f"Copied inference.py to {inference_dst}")
    else:
        logger.warning(f"inference.py not found at {inference_src}")
    
    # Copy model.py
    model_src = os.path.join(src_dir, 'model.py')
    model_dst = os.path.join(code_dir, 'model.py')
    if os.path.exists(model_src):
        shutil.copy2(model_src, model_dst)
        logger.info(f"Copied model.py to {model_dst}")
    else:
        logger.warning(f"model.py not found at {model_src}")'''
    
    new_code = '''    # Copy inference.py and model.py
    # In SageMaker, source code is in /opt/ml/code/ or same directory as train.py
    # Try multiple locations to find the files
    possible_src_dirs = [
        '/opt/ml/code',  # SageMaker default
        os.path.dirname(os.path.abspath(__file__)),  # Same directory as train.py
        os.getcwd(),  # Current working directory
    ]
    
    files_to_copy = ['inference.py', 'model.py']
    
    for filename in files_to_copy:
        copied = False
        for src_dir in possible_src_dirs:
            src_path = os.path.join(src_dir, filename)
            if os.path.exists(src_path):
                dst_path = os.path.join(code_dir, filename)
                shutil.copy2(src_path, dst_path)
                logger.info(f"Copied {filename} from {src_path} to {dst_path}")
                copied = True
                break
        
        if not copied:
            logger.warning(f"{filename} not found in any of: {possible_src_dirs}")
            # List what files ARE available for debugging
            for src_dir in possible_src_dirs:
                if os.path.exists(src_dir):
                    files = os.listdir(src_dir)
                    logger.info(f"Files in {src_dir}: {files}")'''
    
    if old_code not in content:
        print("\nERROR: Could not find the code section to replace!")
        print("The train.py file may have been modified.")
        return False
    
    # Replace the code
    content = content.replace(old_code, new_code)
    
    # Write back
    with open('src/train.py', 'w') as f:
        f.write(content)
    
    print("\n[+] Updated src/train.py with correct inference code paths")
    print("    - Now checks /opt/ml/code/ (SageMaker default)")
    print("    - Falls back to script directory")
    print("    - Falls back to current working directory")
    print("    - Logs available files for debugging")
    
    return True

def upload_training_code():
    """Package and upload updated training code to S3."""
    
    print("\n" + "="*70)
    print("PACKAGING AND UPLOADING TRAINING CODE")
    print("="*70)
    
    # Create tarball
    tmp_path = os.path.join(tempfile.gettempdir(), 'sourcedir_fixed.tar.gz')
    
    # Remove if exists
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)
    
    print(f"\nCreating tarball: {tmp_path}")
    
    with tarfile.open(tmp_path, 'w:gz') as tar:
        # Add train.py
        tar.add('src/train.py', arcname='train.py')
        print("  [+] Added train.py")
        
        # Add model.py
        tar.add('src/model.py', arcname='model.py')
        print("  [+] Added model.py")
        
        # Add inference.py
        tar.add('src/inference.py', arcname='inference.py')
        print("  [+] Added inference.py")
    
    # Upload to S3
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket = 'amzn-s3-movielens-327030626634'
    key = 'training-code/sourcedir.tar.gz'
    
    print(f"\nUploading to s3://{bucket}/{key}")
    s3.upload_file(tmp_path, bucket, key)
    print("[+] Upload complete")
    
    # Cleanup
    os.unlink(tmp_path)
    
    print("\n" + "="*70)
    print("TRAINING CODE UPDATED SUCCESSFULLY")
    print("="*70)
    print("\nNext steps:")
    print("1. Start new pipeline execution:")
    print("   python start_pipeline.py --region us-east-1")
    print("\n2. Monitor execution:")
    print("   python check_execution_status.py --execution-arn <arn>")
    print("\n3. After training completes, verify model artifacts:")
    print("   python inspect_model_artifacts.py")
    print("="*70)

def main():
    """Main function."""
    print("\n" + "="*70)
    print("ISSUE #26: INFERENCE CODE NOT BEING COPIED")
    print("="*70)
    print("\nProblem:")
    print("  - Training script looks for inference.py in wrong location")
    print("  - SageMaker extracts code to /opt/ml/code/")
    print("  - Script was checking os.path.dirname(__file__)")
    print("  - Files not found, not copied to model artifacts")
    print("\nSolution:")
    print("  - Check multiple possible locations")
    print("  - Start with /opt/ml/code/ (SageMaker default)")
    print("  - Fall back to other locations")
    print("  - Log available files for debugging")
    
    # Fix the training script
    if not fix_training_script():
        return
    
    # Upload to S3
    upload_training_code()

if __name__ == '__main__':
    main()
