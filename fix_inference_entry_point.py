"""
Fix inference entry point configuration in the state machine.

The issue: SageMaker PyTorch container is using the default handler which expects
a TorchScript model (torch.jit.load), but we're providing a state dict model.

Solution: Add environment variables to tell SageMaker to use our custom inference.py
"""

import boto3
import json

def fix_inference_entry_point():
    """Update state machine to use custom inference handler."""
    
    sfn_client = boto3.client('stepfunctions', region_name='us-east-1')
    s3_client = boto3.client('s3', region_name='us-east-1')
    
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING INFERENCE ENTRY POINT")
    print("="*70 + "\n")
    
    # Step 1: Package inference code
    print("Step 1: Packaging inference code...")
    
    import tarfile
    import os
    
    # Create inference code tarball
    with tarfile.open('inference_code.tar.gz', 'w:gz') as tar:
        tar.add('src/inference.py', arcname='inference.py')
        tar.add('src/model.py', arcname='model.py')
    
    print("  ✓ Created inference_code.tar.gz")
    
    # Upload to S3
    s3_client.upload_file(
        'inference_code.tar.gz',
        bucket_name,
        'code/inference_code.tar.gz'
    )
    
    print(f"  ✓ Uploaded to s3://{bucket_name}/code/inference_code.tar.gz")
    
    # Clean up local file
    os.remove('inference_code.tar.gz')
    
    # Step 2: Update state machine
    print("\nStep 2: Updating state machine...")
    
    # Get state machine
    state_machines = sfn_client.list_state_machines()
    
    pipeline_sm = None
    for sm in state_machines['stateMachines']:
        if 'MovieLensMLPipeline' in sm['name']:
            pipeline_sm = sm
            break
    
    if not pipeline_sm:
        print("ERROR: Could not find MovieLensMLPipeline state machine")
        return
    
    print(f"  Found: {pipeline_sm['name']}")
    
    # Get current definition
    response = sfn_client.describe_state_machine(
        stateMachineArn=pipeline_sm['stateMachineArn']
    )
    
    definition = json.loads(response['definition'])
    
    # Update CreateModel step
    if 'CreateModel' in definition['States']:
        create_model = definition['States']['CreateModel']
        
        if 'Parameters' in create_model and 'PrimaryContainer' in create_model['Parameters']:
            container = create_model['Parameters']['PrimaryContainer']
            
            # Add environment variables for custom inference handler
            container['Environment'] = {
                'SAGEMAKER_PROGRAM': 'inference.py',
                'SAGEMAKER_SUBMIT_DIRECTORY': f's3://{bucket_name}/code/inference_code.tar.gz',
                'SAGEMAKER_REGION': 'us-east-1'
            }
            
            print("  ✓ Added environment variables to PrimaryContainer:")
            print(f"    - SAGEMAKER_PROGRAM: inference.py")
            print(f"    - SAGEMAKER_SUBMIT_DIRECTORY: s3://{bucket_name}/code/inference_code.tar.gz")
            print(f"    - SAGEMAKER_REGION: us-east-1")
    
    # Update state machine
    try:
        sfn_client.update_state_machine(
            stateMachineArn=pipeline_sm['stateMachineArn'],
            definition=json.dumps(definition)
        )
        print("\n  ✓ State machine updated successfully")
        
    except Exception as e:
        print(f"\nERROR updating state machine: {e}")
        return
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Delete the failed endpoint:")
    print("   aws sagemaker delete-endpoint --endpoint-name movielens-endpoint-20260122-155327-140")
    print("\n2. Start a new pipeline execution:")
    print("   python start_pipeline.py")
    print("\n3. Monitor the execution:")
    print("   python monitor_pipeline.py")
    print()

if __name__ == '__main__':
    fix_inference_entry_point()
