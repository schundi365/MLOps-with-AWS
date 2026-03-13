#!/usr/bin/env python3
"""
Fix Issue #24: State machine not waiting for async operations to complete.

Problem: Training completed in 5 minutes (should be 60), endpoint creation was instant.
This means Step Functions is NOT waiting for SageMaker operations to complete.

Root Cause: Missing .sync suffix on SageMaker resource ARNs:
- createTrainingJob needs .sync
- createModel needs .sync  
- createEndpointConfig needs .sync
- createEndpoint needs .sync

Solution: Add .sync to all SageMaker operations so Step Functions waits for completion.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #24: State Machine Not Waiting for Async Operations")
    print("="*70)
    print()
    
    print("Problem: Training completed in 5 min (should be 60 min)")
    print("         Endpoint creation was instant (should be 5-8 min)")
    print("Root Cause: Missing .sync suffix on SageMaker operations")
    print("Solution: Add .sync to make Step Functions wait for completion")
    print()
    
    # Get current state machine
    sfn_client = boto3.client('stepfunctions', region_name=region)
    state_machine_name = 'MovieLensMLPipeline'
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:{state_machine_name}"
    
    print(f"Fetching current state machine: {state_machine_name}")
    
    try:
        response = sfn_client.describe_state_machine(
            stateMachineArn=state_machine_arn
        )
        
        definition = json.loads(response['definition'])
        role_arn = response['roleArn']
        
        print("[OK] State machine fetched")
        print()
        
        # Fix ModelTraining - add .sync
        print("Fixing ModelTraining resource...")
        if 'ModelTraining' in definition['States']:
            old_resource = definition['States']['ModelTraining']['Resource']
            new_resource = "arn:aws:states:::sagemaker:createTrainingJob.sync"
            definition['States']['ModelTraining']['Resource'] = new_resource
            print(f"  Old: {old_resource}")
            print(f"  New: {new_resource}")
            print("[OK] ModelTraining fixed")
        
        # Fix CreateModel - add .sync
        print()
        print("Fixing CreateModel resource...")
        if 'CreateModel' in definition['States']:
            old_resource = definition['States']['CreateModel']['Resource']
            new_resource = "arn:aws:states:::sagemaker:createModel.sync"
            definition['States']['CreateModel']['Resource'] = new_resource
            print(f"  Old: {old_resource}")
            print(f"  New: {new_resource}")
            print("[OK] CreateModel fixed")
        
        # Fix CreateEndpointConfig - add .sync
        print()
        print("Fixing CreateEndpointConfig resource...")
        if 'CreateEndpointConfig' in definition['States']:
            old_resource = definition['States']['CreateEndpointConfig']['Resource']
            new_resource = "arn:aws:states:::sagemaker:createEndpointConfig.sync"
            definition['States']['CreateEndpointConfig']['Resource'] = new_resource
            print(f"  Old: {old_resource}")
            print(f"  New: {new_resource}")
            print("[OK] CreateEndpointConfig fixed")
        
        # Fix CreateEndpoint - add .sync
        print()
        print("Fixing CreateEndpoint resource...")
        if 'CreateEndpoint' in definition['States']:
            old_resource = definition['States']['CreateEndpoint']['Resource']
            new_resource = "arn:aws:states:::sagemaker:createEndpoint.sync"
            definition['States']['CreateEndpoint']['Resource'] = new_resource
            print(f"  Old: {old_resource}")
            print(f"  New: {new_resource}")
            print("[OK] CreateEndpoint fixed")
        
        # Update state machine
        print()
        print("Updating state machine in AWS...")
        sfn_client.update_state_machine(
            stateMachineArn=state_machine_arn,
            definition=json.dumps(definition),
            roleArn=role_arn
        )
        
        print("[OK] State machine updated")
        
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("="*70)
    print("FIX APPLIED")
    print("="*70)
    print()
    print("What .sync does:")
    print("  - Step Functions WAITS for SageMaker job to complete")
    print("  - Training will now take ~60 minutes (not 5 minutes)")
    print("  - Endpoint creation will take 5-8 minutes (not instant)")
    print("  - Evaluation will run AFTER endpoint is InService")
    print()
    print("Expected timeline for next execution:")
    print("  - Preprocessing: 5-10 minutes")
    print("  - Training: 60 minutes (WILL WAIT)")
    print("  - PrepareDeployment: <1 minute")
    print("  - CreateModel: 2 minutes (WILL WAIT)")
    print("  - CreateEndpointConfig: 1 minute (WILL WAIT)")
    print("  - CreateEndpoint: 5-8 minutes (WILL WAIT)")
    print("  - ModelEvaluation: 2-5 minutes")
    print("  - Total: ~80-90 minutes")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
