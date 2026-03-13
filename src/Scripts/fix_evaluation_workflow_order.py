#!/usr/bin/env python3
"""
Fix Issue #21: Evaluation trying to invoke non-existent endpoint.

Problem: The workflow is Training → Evaluation → Deploy, but evaluation
tries to invoke an endpoint that doesn't exist yet.

Solution: Change workflow to Training → Deploy → Evaluation, so the endpoint
exists when evaluation runs.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #21: Evaluation Workflow Order")
    print("="*70)
    print()
    
    print("Problem: Evaluation runs before deployment")
    print("Current: Training → Evaluation → Deploy")
    print("Fixed: Training → Deploy → Evaluation")
    print()
    print("Reason: Evaluation needs endpoint to exist for predictions")
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
        
        # Update workflow order
        print("Updating workflow order...")
        print()
        
        # Change ModelTraining to go to ModelDeployment instead of ModelEvaluation
        definition['States']['ModelTraining']['Next'] = 'ModelDeployment'
        print("[OK] ModelTraining now goes to ModelDeployment")
        
        # Change ModelDeployment to go to ModelEvaluation instead of MonitoringSetup
        definition['States']['ModelDeployment']['Next'] = 'ModelEvaluation'
        print("[OK] ModelDeployment now goes to ModelEvaluation")
        
        # Change ModelEvaluation to go to CheckEvaluationResult (keep this)
        # Already correct
        
        # Change CheckEvaluationResult success to go to MonitoringSetup instead of ModelDeployment
        definition['States']['CheckEvaluationResult']['Choices'][0]['Next'] = 'MonitoringSetup'
        print("[OK] CheckEvaluationResult now goes to MonitoringSetup")
        
        # Update state machine
        print()
        print("Updating state machine...")
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
    print("New workflow order:")
    print("  1. DataPreprocessing")
    print("  2. ModelTraining")
    print("  3. ModelDeployment      <- MOVED UP")
    print("  4. ModelEvaluation      <- MOVED DOWN")
    print("  5. CheckEvaluationResult")
    print("  6. MonitoringSetup")
    print("  7. PipelineSucceeded")
    print()
    print("Now the endpoint will exist when evaluation runs!")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
