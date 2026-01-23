"""
Check the current state machine hyperparameters.
"""

import boto3
import json

def check_hyperparameters():
    """Check hyperparameters in state machine."""
    
    sfn = boto3.client('stepfunctions', region_name='us-east-1')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    state_machine_arn = f"arn:aws:states:us-east-1:{account_id}:stateMachine:MovieLensMLPipeline"
    
    print("\n" + "="*70)
    print("STATE MACHINE HYPERPARAMETERS")
    print("="*70 + "\n")
    
    try:
        response = sfn.describe_state_machine(stateMachineArn=state_machine_arn)
        definition = json.loads(response['definition'])
        
        hyperparameters = definition['States']['ModelTraining']['Parameters']['HyperParameters']
        
        print("Current Hyperparameters:")
        print("-" * 70)
        for key, value in hyperparameters.items():
            print(f"  {key}: {value}")
        
        print("\n" + "="*70)
        print("ANALYSIS")
        print("="*70 + "\n")
        
        # Check for required parameters
        required = ['sagemaker_program', 'sagemaker_submit_directory']
        missing = []
        
        for param in required:
            if param not in hyperparameters:
                missing.append(param)
                print(f"❌ MISSING: {param}")
            else:
                print(f"✓ Found: {param} = {hyperparameters[param]}")
        
        if missing:
            print(f"\n⚠ Missing required parameters: {missing}")
            print("\nThe training container needs:")
            print("  • sagemaker_program: Name of the entry point script (e.g., 'train.py')")
            print("  • sagemaker_submit_directory: S3 path to the code tarball")
        else:
            print("\n✓ All required parameters present")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    check_hyperparameters()
