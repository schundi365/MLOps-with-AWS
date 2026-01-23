#!/usr/bin/env python3
"""
Fix Issue #25: Missing inference code in model artifacts.

Problem: The endpoint crashes with "Worker died" because the model.tar.gz
doesn't contain the inference.py and model.py files needed to load the model.

Root Cause: Training script only saves model.pth and metadata.json, but
SageMaker PyTorch inference container needs:
- inference.py (with model_fn, input_fn, predict_fn, output_fn)
- model.py (CollaborativeFilteringModel class definition)

Solution: Update training script to copy inference.py and model.py into
the model directory before SageMaker packages it into model.tar.gz.
"""

import boto3
import os
import shutil

def main():
    print("\n" + "="*70)
    print("FIXING ISSUE #25: Missing Inference Code in Model Artifacts")
    print("="*70)
    print()
    
    print("Problem: Endpoint crashes with 'Worker died'")
    print("Root Cause: model.tar.gz missing inference.py and model.py")
    print("Solution: Update train.py to include these files")
    print()
    
    # Read current train.py
    train_py_path = 'src/train.py'
    
    print(f"Reading {train_py_path}...")
    with open(train_py_path, 'r') as f:
        content = f.read()
    
    # Find the save_model function and update it
    print("Updating save_model function...")
    
    # Find the function
    import_section = '''import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional
import shutil'''
    
    if 'import shutil' not in content:
        # Add shutil import
        content = content.replace(
            'import sys',
            'import sys\nimport shutil'
        )
        print("[OK] Added shutil import")
    
    # Find and update save_model function
    old_save_model = '''def save_model(model: nn.Module, model_dir: str, num_users: int,
               num_movies: int, embedding_dim: int, metadata: dict):
    """
    Save final model to SageMaker model directory.
    
    Args:
        model: Trained model
        model_dir: Directory to save model
        num_users: Number of users in training data
        num_movies: Number of movies in training data
        embedding_dim: Embedding dimensionality
        metadata: Additional metadata to save
    """
    # Create model directory if it doesn't exist
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model state dict
    model_path = os.path.join(model_dir, 'model.pth')
    torch.save(model.state_dict(), model_path)
    logger.info(f"Saved model to {model_path}")
    
    # Save metadata
    # Convert numpy types to native Python types for JSON serialization
    metadata_dict = {
        'num_users': int(num_users),
        'num_movies': int(num_movies),
        'embedding_dim': int(embedding_dim),
        **metadata
    }
    metadata_path = os.path.join(model_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata_dict, f, indent=2)
    logger.info(f"Saved metadata to {metadata_path}")'''
    
    new_save_model = '''def save_model(model: nn.Module, model_dir: str, num_users: int,
               num_movies: int, embedding_dim: int, metadata: dict):
    """
    Save final model to SageMaker model directory.
    
    Args:
        model: Trained model
        model_dir: Directory to save model
        num_users: Number of users in training data
        num_movies: Number of movies in training data
        embedding_dim: Embedding dimensionality
        metadata: Additional metadata to save
    """
    # Create model directory if it doesn't exist
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model state dict
    model_path = os.path.join(model_dir, 'model.pth')
    torch.save(model.state_dict(), model_path)
    logger.info(f"Saved model to {model_path}")
    
    # Save metadata
    # Convert numpy types to native Python types for JSON serialization
    metadata_dict = {
        'num_users': int(num_users),
        'num_movies': int(num_movies),
        'embedding_dim': int(embedding_dim),
        **metadata
    }
    metadata_path = os.path.join(model_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata_dict, f, indent=2)
    logger.info(f"Saved metadata to {metadata_path}")
    
    # Copy inference code files for SageMaker endpoint
    # These files are needed by the PyTorch inference container
    code_dir = os.path.join(model_dir, 'code')
    os.makedirs(code_dir, exist_ok=True)
    
    # Copy inference.py
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
        logger.warning(f"model.py not found at {model_src}")
    
    logger.info("Model artifacts saved successfully with inference code")'''
    
    if old_save_model in content:
        content = content.replace(old_save_model, new_save_model)
        print("[OK] Updated save_model function")
    else:
        print("[!] Could not find exact save_model function to replace")
        print("    Manual update may be needed")
        return
    
    # Write updated content
    print(f"Writing updated {train_py_path}...")
    with open(train_py_path, 'w') as f:
        f.write(content)
    
    print("[OK] File updated")
    
    # Now we need to re-upload the training code to S3
    print()
    print("Uploading updated training code to S3...")
    
    bucket_name = 'amzn-s3-movielens-327030626634'
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    # Package training code
    import tarfile
    import tempfile
    
    with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
        tmp_path = tmp.name
    
    print(f"Creating tarball: {tmp_path}")
    with tarfile.open(tmp_path, 'w:gz') as tar:
        tar.add('src/train.py', arcname='train.py')
        tar.add('src/model.py', arcname='model.py')
        tar.add('src/inference.py', arcname='inference.py')
    
    print("[OK] Tarball created")
    
    # Upload to S3
    s3_key = 'training-code/sourcedir.tar.gz'
    print(f"Uploading to s3://{bucket_name}/{s3_key}")
    s3_client.upload_file(tmp_path, bucket_name, s3_key)
    
    print("[OK] Training code uploaded")
    
    # Clean up
    os.unlink(tmp_path)
    
    print()
    print("="*70)
    print("FIX APPLIED")
    print("="*70)
    print()
    print("Changes made:")
    print("  1. Updated train.py to copy inference.py and model.py")
    print("  2. Files are copied to model_dir/code/ directory")
    print("  3. SageMaker will package them into model.tar.gz")
    print("  4. Inference container will find them in /opt/ml/model/code/")
    print()
    print("Model artifacts structure:")
    print("  model.tar.gz")
    print("    ├── model.pth")
    print("    ├── metadata.json")
    print("    └── code/")
    print("        ├── inference.py")
    print("        └── model.py")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
