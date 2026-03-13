"""
Fix inference handler by ensuring proper entry point configuration.

The issue is that SageMaker is using the default PyTorch handler which expects
a TorchScript model, but we're providing a state dict. We need to ensure our
custom inference.py is used as the entry point.
"""

import boto3
import json

def fix_inference_handler():
    """Update Step Functions state machine to use custom inference handler."""
    
    sfn_client = boto3.client('stepfunctions', region_name='us-east-1')
    
    # Get current state machine
    state_machines = sfn_client.list_state_machines()
    
    pipeline_sm = None
    for sm in state_machines['stateMachines']:
        if 'MovieLensMLPipeline' in sm['name']:
            pipeline_sm = sm
            break
    
    if not pipeline_sm:
        print("ERROR: Could not find MovieLensMLPipeline state machine")
        return
    
    print(f"Found state machine: {pipeline_sm['name']}")
    
    # Get current definition
    response = sfn_client.describe_state_machine(
        stateMachineArn=pipeline_sm['stateMachineArn']
    )
    
    definition = json.loads(response['definition'])
    
    # Update the CreateModel step to include inference code
    if 'CreateModel' in definition['States']:
        create_model = definition['States']['CreateModel']
        
        # Ensure PrimaryContainer has the correct configuration
        if 'Parameters' in create_model:
            params = create_model['Parameters']
            
            # Update PrimaryContainer to use our inference script
            if 'PrimaryContainer' in params:
                container = params['PrimaryContainer']
                
                # Set the entry point to use our inference.py
                container['Environment'] = {
                    'SAGEMAKER_PROGRAM': 'inference.py',
                    'SAGEMAKER_SUBMIT_DIRECTORY': 's3://movielens-ml-pipeline-327030626634/code/inference.tar.gz'
                }
                
                print("Updated PrimaryContainer environment variables")
    
    # Update state machine
    try:
        sfn_client.update_state_machine(
            stateMachineArn=pipeline_sm['stateMachineArn'],
            definition=json.dumps(definition)
        )
        print(f"\n✓ Successfully updated state machine")
        print(f"  - Added SAGEMAKER_PROGRAM environment variable")
        print(f"  - Added SAGEMAKER_SUBMIT_DIRECTORY environment variable")
        
    except Exception as e:
        print(f"\nERROR updating state machine: {e}")

if __name__ == '__main__':
    fix_inference_handler()
