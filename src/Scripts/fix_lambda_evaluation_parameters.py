#!/usr/bin/env python3
"""
Fix Issue #20: Lambda evaluation function missing required parameters.

Problem: Step Functions passes {model_data, bucket_name} but Lambda expects
{test_data_bucket, test_data_key, endpoint_name, metrics_bucket, metrics_key}.

Solution: Update Step Functions state machine to pass correct parameters.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #20: Lambda Evaluation Parameters")
    print("="*70)
    print()
    
    print("Problem: Step Functions passes wrong parameters to Lambda")
    print("Current: {model_data, bucket_name}")
    print("Expected: {test_data_bucket, test_data_key, endpoint_name, metrics_bucket, metrics_key}")
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
        
        # Update ModelEvaluation step parameters
        print("Updating ModelEvaluation step parameters...")
        
        old_params = definition['States']['ModelEvaluation']['Parameters']
        print(f"Old parameters: {json.dumps(old_params, indent=2)}")
        print()
        
        # New parameters that match Lambda expectations
        new_params = {
            "test_data_bucket": bucket_name,
            "test_data_key": "processed-data/test.csv",
            "endpoint_name.$": "$.endpoint_name",
            "metrics_bucket": bucket_name,
            "metrics_key": "metrics/evaluation_results.json"
        }
        
        definition['States']['ModelEvaluation']['Parameters'] = new_params
        
        print(f"New parameters: {json.dumps(new_params, indent=2)}")
        print()
        
        # Update state machine
        print("Updating state machine...")
        sfn_client.update_state_machine(
            stateMachineArn=state_machine_arn,
            definition=json.dumps(definition),
            roleArn=role_arn
        )
        
        print("[OK] State machine updated")
        
    except Exception as e:
        print(f"[X] Error: {e}")
        return
    
    print()
    print("="*70)
    print("FIX APPLIED")
    print("="*70)
    print()
    print("Changes made:")
    print("1. Updated ModelEvaluation step parameters")
    print("2. Added test_data_bucket and test_data_key")
    print("3. Added endpoint_name (from state)")
    print("4. Added metrics_bucket and metrics_key")
    print()
    print("The Lambda function will now receive all required parameters!")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
