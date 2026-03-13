"""
Package Training Code for SageMaker

SageMaker PyTorch requires code to be in a tarball (sourcedir.tar.gz).
This script creates the tarball and uploads it to S3.

Usage:
    python package_training_code.py --bucket <bucket-name>
"""
import boto3
import tarfile
import argparse
import os
from pathlib import Path


def create_tarball():
    """Create tarball with training code"""
    
    print("\n" + "="*70)
    print("CREATING TRAINING CODE TARBALL")
    print("="*70 + "\n")
    
    # Files to include
    files_to_package = [
        'src/train.py',
        'src/model.py'
    ]
    
    # Create tarball
    tarball_name = 'sourcedir.tar.gz'
    
    print(f"[...] Creating {tarball_name}")
    
    with tarfile.open(tarball_name, 'w:gz') as tar:
        for file_path in files_to_package:
            if os.path.exists(file_path):
                # Add file with just the filename (no directory structure)
                arcname = os.path.basename(file_path)
                tar.add(file_path, arcname=arcname)
                print(f"[OK] Added {file_path} as {arcname}")
            else:
                print(f"[X] File not found: {file_path}")
                return None
    
    # Verify tarball
    if os.path.exists(tarball_name):
        size = os.path.getsize(tarball_name)
        print(f"\n[OK] Created {tarball_name} ({size} bytes)")
        
        # List contents
        print("\n[INFO] Tarball contents:")
        with tarfile.open(tarball_name, 'r:gz') as tar:
            for member in tar.getmembers():
                print(f"  - {member.name} ({member.size} bytes)")
        
        return tarball_name
    else:
        print(f"[X] Failed to create {tarball_name}")
        return None


def upload_tarball(bucket_name: str, tarball_path: str):
    """Upload tarball to S3"""
    
    s3 = boto3.client('s3')
    
    print("\n" + "="*70)
    print("UPLOADING TARBALL TO S3")
    print("="*70 + "\n")
    
    s3_key = 'code/sourcedir.tar.gz'
    
    try:
        print(f"[...] Uploading to s3://{bucket_name}/{s3_key}")
        s3.upload_file(tarball_path, bucket_name, s3_key)
        
        # Verify upload
        response = s3.head_object(Bucket=bucket_name, Key=s3_key)
        size = response['ContentLength']
        print(f"[OK] Uploaded {s3_key} ({size} bytes)")
        
        return True
        
    except Exception as e:
        print(f"[X] Error uploading: {e}")
        return False


def update_state_machine(bucket_name: str, region: str = 'us-east-1'):
    """Update state machine to use tarball"""
    
    import json
    sfn = boto3.client('stepfunctions', region_name=region)
    
    print("\n" + "="*70)
    print("UPDATING STATE MACHINE")
    print("="*70 + "\n")
    
    state_machine_name = 'MovieLensMLPipeline'
    
    try:
        # Get state machine
        response = sfn.list_state_machines()
        state_machine_arn = None
        
        for sm in response['stateMachines']:
            if sm['name'] == state_machine_name:
                state_machine_arn = sm['stateMachineArn']
                break
        
        if not state_machine_arn:
            print(f"[X] State machine not found: {state_machine_name}")
            return False
        
        print(f"[OK] Found state machine")
        
        # Get current definition
        response = sfn.describe_state_machine(stateMachineArn=state_machine_arn)
        definition = json.loads(response['definition'])
        
        # Update ModelTraining state
        if 'States' in definition and 'ModelTraining' in definition['States']:
            training_state = definition['States']['ModelTraining']
            
            if 'Parameters' in training_state and 'HyperParameters' in training_state['Parameters']:
                hyper_params = training_state['Parameters']['HyperParameters']
                
                # Update to use tarball
                hyper_params['sagemaker_program'] = 'train.py'
                hyper_params['sagemaker_submit_directory'] = f's3://{bucket_name}/code/sourcedir.tar.gz'
                
                print("[OK] Updated HyperParameters:")
                print(f"     sagemaker_program: train.py")
                print(f"     sagemaker_submit_directory: s3://{bucket_name}/code/sourcedir.tar.gz")
            else:
                print("[X] Could not find HyperParameters")
                return False
        else:
            print("[X] Could not find ModelTraining state")
            return False
        
        # Update state machine
        print("\n[...] Updating state machine definition")
        
        sfn.update_state_machine(
            stateMachineArn=state_machine_arn,
            definition=json.dumps(definition)
        )
        
        print("[OK] State machine updated")
        
        return True
        
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Package training code as tarball for SageMaker'
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
    
    # Create tarball
    tarball = create_tarball()
    if not tarball:
        print("\n[X] Failed to create tarball")
        return 1
    
    # Upload tarball
    if not upload_tarball(args.bucket, tarball):
        print("\n[X] Failed to upload tarball")
        return 1
    
    # Update state machine
    if not update_state_machine(args.bucket, args.region):
        print("\n[X] Failed to update state machine")
        return 1
    
    # Cleanup local tarball
    if os.path.exists(tarball):
        os.remove(tarball)
        print(f"\n[OK] Cleaned up local {tarball}")
    
    print("\n" + "="*70)
    print("TRAINING CODE PACKAGED!")
    print("="*70)
    print("\nThe training code is now properly packaged as:")
    print(f"  s3://{args.bucket}/code/sourcedir.tar.gz")
    print("\nContents:")
    print("  - train.py (training script)")
    print("  - model.py (model definition)")
    print("\nYou can now restart the pipeline:")
    print(f"  python start_pipeline.py --region {args.region}")
    print("\n" + "="*70 + "\n")
    
    return 0


if __name__ == '__main__':
    import sys
    import json
    sys.exit(main())
