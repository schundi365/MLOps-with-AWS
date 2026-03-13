"""
Final fix for inference handler - package inference code WITH model artifacts.

The issue: SAGEMAKER_SUBMIT_DIRECTORY environment variable only works during
training, not during inference. For inference, the code must be IN the model
artifacts directory.

Solution: Modify the training script to include inference code in model artifacts,
then repackage existing model artifacts to include the inference code.
"""

import boto3
import json
import tarfile
import io
import os
import tempfile

def fix_inference_handler():
    """
    Fix inference by repackaging model artifacts to include inference code.
    """
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FINAL FIX: REPACKAGE MODEL ARTIFACTS WITH INFERENCE CODE")
    print("="*70 + "\n")
    
    # The real solution is to modify the training script to include inference
    # code in the model artifacts. But for now, let's document the proper approach.
    
    print("ROOT CAUSE:")
    print("-" * 70)
    print("The SAGEMAKER_SUBMIT_DIRECTORY environment variable only works")
    print("during TRAINING, not during INFERENCE.")
    print()
    print("For inference, SageMaker PyTorch containers look for code in:")
    print("  1. /opt/ml/model/code/ directory (inside model artifacts)")
    print("  2. The model artifacts must contain a 'code' directory")
    print()
    
    print("PROPER SOLUTION:")
    print("-" * 70)
    print("Modify src/train.py to package inference code WITH the model:")
    print()
    print("In src/train.py, after saving the model, add:")
    print("""
    # Create code directory in model artifacts
    code_dir = os.path.join(args.model_dir, 'code')
    os.makedirs(code_dir, exist_ok=True)
    
    # Copy inference files
    import shutil
    shutil.copy('inference.py', os.path.join(code_dir, 'inference.py'))
    shutil.copy('model.py', os.path.join(code_dir, 'model.py'))
    """)
    print()
    
    print("ALTERNATIVE WORKAROUND:")
    print("-" * 70)
    print("We can repackage the EXISTING model artifacts to include the code.")
    print("This avoids retraining but requires downloading and re-uploading.")
    print()
    
    # Check if we should proceed with workaround
    response = input("Apply workaround to repackage existing model? (yes/no): ")
    
    if response.lower() != 'yes':
        print("\nSkipping workaround. Please modify src/train.py and retrain.")
        return
    
    print("\nApplying workaround...")
    print()
    
    # Find the latest model artifacts
    print("Step 1: Finding latest model artifacts...")
    
    # List objects in models directory
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix='models/',
        Delimiter='/'
    )
    
    if 'Contents' not in response:
        print("ERROR: No model artifacts found in s3://{}/models/".format(bucket_name))
        return
    
    # Find the most recent model.tar.gz
    model_objects = [obj for obj in response['Contents'] if obj['Key'].endswith('model.tar.gz')]
    
    if not model_objects:
        print("ERROR: No model.tar.gz files found")
        return
    
    # Sort by last modified
    model_objects.sort(key=lambda x: x['LastModified'], reverse=True)
    latest_model = model_objects[0]
    
    print(f"  Found: s3://{bucket_name}/{latest_model['Key']}")
    print(f"  Size: {latest_model['Size']} bytes")
    print(f"  Modified: {latest_model['LastModified']}")
    print()
    
    # Download model artifacts
    print("Step 2: Downloading model artifacts...")
    model_obj = s3_client.get_object(Bucket=bucket_name, Key=latest_model['Key'])
    model_data = model_obj['Body'].read()
    print(f"  Downloaded {len(model_data)} bytes")
    print()
    
    # Extract model artifacts
    print("Step 3: Extracting model artifacts...")
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract original model
        model_tar = tarfile.open(fileobj=io.BytesIO(model_data))
        model_tar.extractall(tmpdir)
        model_tar.close()
        
        print(f"  Extracted to {tmpdir}")
        print("  Contents:")
        for root, dirs, files in os.walk(tmpdir):
            level = root.replace(tmpdir, '').count(os.sep)
            indent = ' ' * 4 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
        print()
        
        # Create code directory
        print("Step 4: Adding inference code...")
        code_dir = os.path.join(tmpdir, 'code')
        os.makedirs(code_dir, exist_ok=True)
        
        # Copy inference files from src/
        import shutil
        shutil.copy('src/inference.py', os.path.join(code_dir, 'inference.py'))
        shutil.copy('src/model.py', os.path.join(code_dir, 'model.py'))
        
        print("  ✓ Added code/inference.py")
        print("  ✓ Added code/model.py")
        print()
        
        # Repackage
        print("Step 5: Repackaging model artifacts...")
        new_model_path = os.path.join(tmpdir, 'model_with_code.tar.gz')
        
        with tarfile.open(new_model_path, 'w:gz') as tar:
            for item in os.listdir(tmpdir):
                if item != 'model_with_code.tar.gz':
                    tar.add(os.path.join(tmpdir, item), arcname=item)
        
        print(f"  ✓ Created {new_model_path}")
        print()
        
        # Upload to S3
        print("Step 6: Uploading repackaged model...")
        new_key = latest_model['Key'].replace('.tar.gz', '_with_code.tar.gz')
        
        with open(new_model_path, 'rb') as f:
            s3_client.upload_fileobj(f, bucket_name, new_key)
        
        print(f"  ✓ Uploaded to s3://{bucket_name}/{new_key}")
        print()
    
    print("="*70)
    print("WORKAROUND COMPLETE")
    print("="*70)
    print()
    print("The repackaged model is at:")
    print(f"  s3://{bucket_name}/{new_key}")
    print()
    print("NEXT STEPS:")
    print("1. Update the state machine to use the new model location")
    print("2. OR manually create an endpoint with the new model")
    print("3. OR (RECOMMENDED) modify src/train.py and retrain")
    print()
    print("To test the repackaged model manually:")
    print(f"  aws sagemaker create-model \\")
    print(f"    --model-name movielens-test-model \\")
    print(f"    --primary-container Image=763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.0.0-cpu-py310,ModelDataUrl=s3://{bucket_name}/{new_key} \\")
    print(f"    --execution-role-arn arn:aws:iam::327030626634:role/MovieLensSageMakerRole")
    print()

if __name__ == '__main__':
    fix_inference_handler()
