"""
Fix missing sagemaker_program and sagemaker_submit_directory parameters.

Issue: When fixing hyperparameter names, we accidentally removed the required
SageMaker parameters that tell the container which script to run.
"""

import boto3
import json

def fix_sagemaker_parameters():
    """Add back the missing SageMaker parameters."""
    
    sfn = boto3.client('stepfunctions', region_name='us-east-1')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    bucket_name = 'amzn-s3-movielens-327030626634'
    state_machine_name = 'MovieLensMLPipeline'
    state_machine_arn = f"arn:aws:states:us-east-1:{account_id}:stateMachine:{state_machine_name}"
    
    print("="*70)
    print("FIXING MISSING SAGEMAKER PARAMETERS")
    print("="*70)
    print()
    
    # Get current state machine definition
    print("1. Fetching current state machine definition...")
    try:
        response = sfn.describe_state_machine(stateMachineArn=state_machine_arn)
        definition = json.loads(response['definition'])
        role_arn = response['roleArn']
        print("   ✓ Retrieved state machine definition")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    # Update hyperparameters
    print("\n2. Adding missing SageMaker parameters...")
    print("   Current hyperparameters:")
    current_params = definition['States']['ModelTraining']['Parameters']['HyperParameters']
    for key, value in current_params.items():
        print(f"      {key}: {value}")
    
    # Add the missing parameters
    definition['States']['ModelTraining']['Parameters']['HyperParameters'] = {
        "epochs": "50",
        "batch-size": "256",
        "learning-rate": "0.001",
        "embedding-dim": "128",
        "num-factors": "50",
        "sagemaker_program": "train.py",
        "sagemaker_submit_directory": f"s3://{bucket_name}/code/sourcedir.tar.gz"
    }
    
    print("\n   Updated hyperparameters:")
    new_params = definition['States']['ModelTraining']['Parameters']['HyperParameters']
    for key, value in new_params.items():
        print(f"      {key}: {value}")
    
    # Update the state machine
    print("\n3. Updating state machine...")
    try:
        sfn.update_state_machine(
            stateMachineArn=state_machine_arn,
            definition=json.dumps(definition),
            roleArn=role_arn
        )
        print("   ✓ State machine updated successfully")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False
    
    print("\n" + "="*70)
    print("✓ SAGEMAKER PARAMETERS FIXED")
    print("="*70)
    print()
    print("Added parameters:")
    print("  • sagemaker_program: train.py")
    print(f"  • sagemaker_submit_directory: s3://{bucket_name}/code/sourcedir.tar.gz")
    print()
    print("Next steps:")
    print("  1. Stop the failed training job (if still running)")
    print("  2. Start a new pipeline execution")
    print("  3. Verify training starts correctly")
    print()
    
    return True

if __name__ == '__main__':
    success = fix_sagemaker_parameters()
    exit(0 if success else 1)
