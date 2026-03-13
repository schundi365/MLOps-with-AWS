"""
Fix Training Job Entry Point

This script:
1. Uploads train.py and model.py to S3
2. Updates the Step Functions state machine to include entry point configuration

Usage:
    python fix_training_entrypoint.py --bucket <bucket-name>
"""
import boto3
import json
import argparse


def upload_training_code(bucket_name: str):
    """Upload training scripts to S3"""
    
    s3 = boto3.client('s3')
    
    print("\n" + "="*70)
    print("UPLOADING TRAINING CODE")
    print("="*70 + "\n")
    
    # Files to upload
    files_to_upload = [
        ('src/train.py', 'code/train.py'),
        ('src/model.py', 'code/model.py')
    ]
    
    for local_file, s3_key in files_to_upload:
        try:
            print(f"[...] Uploading {local_file} to s3://{bucket_name}/{s3_key}")
            s3.upload_file(local_file, bucket_name, s3_key)
            
            # Verify upload
            response = s3.head_object(Bucket=bucket_name, Key=s3_key)
            size = response['ContentLength']
            print(f"[OK] Uploaded {s3_key} ({size} bytes)")
            
        except Exception as e:
            print(f"[X] Error uploading {local_file}: {e}")
            return False
    
    return True


def update_state_machine(bucket_name: str, region: str = 'us-east-1'):
    """Update Step Functions state machine to include entry point"""
    
    sfn = boto3.client('stepfunctions', region_name=region)
    iam = boto3.client('iam', region_name=region)
    
    print("\n" + "="*70)
    print("UPDATING STATE MACHINE")
    print("="*70 + "\n")
    
    state_machine_name = 'MovieLensMLPipeline'
    
    try:
        # Get current state machine
        print(f"[...] Getting state machine: {state_machine_name}")
        
        # List state machines to find ARN
        response = sfn.list_state_machines()
        state_machine_arn = None
        
        for sm in response['stateMachines']:
            if sm['name'] == state_machine_name:
                state_machine_arn = sm['stateMachineArn']
                break
        
        if not state_machine_arn:
            print(f"[X] State machine not found: {state_machine_name}")
            return False
        
        print(f"[OK] Found state machine: {state_machine_arn}")
        
        # Get current definition
        response = sfn.describe_state_machine(stateMachineArn=state_machine_arn)
        definition = json.loads(response['definition'])
        role_arn = response['roleArn']
        
        # Update ModelTraining state
        if 'States' in definition and 'ModelTraining' in definition['States']:
            training_state = definition['States']['ModelTraining']
            
            # Add HyperParameters for entry point
            if 'Parameters' in training_state and 'HyperParameters' in training_state['Parameters']:
                hyper_params = training_state['Parameters']['HyperParameters']
                
                # Add sagemaker_program and sagemaker_submit_directory
                hyper_params['sagemaker_program'] = 'train.py'
                hyper_params['sagemaker_submit_directory'] = f's3://{bucket_name}/code/'
                
                print("[OK] Added entry point configuration to HyperParameters")
                print(f"     sagemaker_program: train.py")
                print(f"     sagemaker_submit_directory: s3://{bucket_name}/code/")
            
            else:
                print("[X] Could not find HyperParameters in training state")
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
        
        print("[OK] State machine updated successfully")
        
        return True
        
    except Exception as e:
        print(f"[X] Error updating state machine: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Fix training job entry point configuration'
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
    
    # Upload training code
    print("Step 1: Upload training code to S3")
    if not upload_training_code(args.bucket):
        print("\n[X] Failed to upload training code")
        return 1
    
    # Update state machine
    print("\nStep 2: Update state machine configuration")
    if not update_state_machine(args.bucket, args.region):
        print("\n[X] Failed to update state machine")
        return 1
    
    print("\n" + "="*70)
    print("TRAINING ENTRY POINT FIXED!")
    print("="*70)
    print("\nThe training job will now:")
    print("  1. Load train.py from s3://{}/code/".format(args.bucket))
    print("  2. Import model.py from the same location")
    print("  3. Execute the training script correctly")
    print("\nYou can now restart the pipeline:")
    print("  python start_pipeline.py --region {}".format(args.region))
    print("\n" + "="*70 + "\n")
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
