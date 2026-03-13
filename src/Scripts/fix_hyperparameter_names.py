"""
Fix hyperparameter names in Step Functions state machine.

Issue: State machine uses underscores (batch_size) but training script expects hyphens (batch-size).
This is a regression of Issue #15.

Solution: Update state machine definition to use hyphenated parameter names.
"""

import boto3
import json

def fix_hyperparameter_names():
    """Fix hyperparameter names in the state machine definition."""
    
    sfn = boto3.client('stepfunctions', region_name='us-east-1')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    state_machine_name = 'MovieLensMLPipeline'
    state_machine_arn = f"arn:aws:states:us-east-1:{account_id}:stateMachine:{state_machine_name}"
    
    print("="*70)
    print("FIXING HYPERPARAMETER NAMES IN STATE MACHINE")
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
    
    # Update hyperparameters in ModelTraining step
    print("\n2. Updating hyperparameters...")
    print("   Current hyperparameters:")
    current_params = definition['States']['ModelTraining']['Parameters']['HyperParameters']
    for key, value in current_params.items():
        print(f"      {key}: {value}")
    
    # Fix the parameter names (use hyphens instead of underscores)
    definition['States']['ModelTraining']['Parameters']['HyperParameters'] = {
        "epochs": "50",
        "batch-size": "256",
        "learning-rate": "0.001",
        "embedding-dim": "128",
        "num-factors": "50"
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
    print("✓ HYPERPARAMETER NAMES FIXED")
    print("="*70)
    print()
    print("Changes made:")
    print("  • batch_size → batch-size")
    print("  • learning_rate → learning-rate")
    print("  • embedding_dim → embedding-dim")
    print("  • num_factors → num-factors")
    print()
    print("Next steps:")
    print("  1. Stop the failed training job (if still running)")
    print("  2. Start a new pipeline execution")
    print("  3. Monitor training logs to verify arguments are parsed correctly")
    print()
    
    return True

if __name__ == '__main__':
    success = fix_hyperparameter_names()
    exit(0 if success else 1)
