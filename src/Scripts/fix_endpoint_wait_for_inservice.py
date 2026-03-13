#!/usr/bin/env python3
"""
Fix Issue #24: Endpoint creation doesn't wait for InService status.

Problem: CreateEndpoint returns immediately, but endpoint takes 5-8 minutes to reach InService.
Evaluation tries to invoke endpoint before it's ready.

Solution: Add a Task state after CreateEndpoint that describes the endpoint in a loop
until it reaches InService status, or use a Lambda function to wait.

Actually, the better solution is to add a Lambda function that waits for endpoint
to be InService before proceeding to evaluation.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #24: Endpoint Not Ready Before Evaluation")
    print("="*70)
    print()
    
    print("Problem: CreateEndpoint returns immediately")
    print("         Endpoint takes 5-8 minutes to reach InService")
    print("         Evaluation runs before endpoint is ready")
    print()
    print("Solution: Add WaitForEndpoint state that polls until InService")
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
        
        # Add WaitForEndpoint state after CreateEndpoint
        print("Adding WaitForEndpoint state...")
        
        wait_for_endpoint = {
            "Type": "Task",
            "Resource": "arn:aws:states:::aws-sdk:sagemaker:describeEndpoint",
            "Parameters": {
                "EndpointName.$": "$.endpoint_name"
            },
            "ResultPath": "$.endpoint_status",
            "Next": "CheckEndpointStatus",
            "Retry": [
                {
                    "ErrorEquals": ["States.TaskFailed"],
                    "IntervalSeconds": 30,
                    "MaxAttempts": 20,
                    "BackoffRate": 1.0
                }
            ]
        }
        
        definition['States']['WaitForEndpoint'] = wait_for_endpoint
        
        # Add CheckEndpointStatus Choice state
        print("Adding CheckEndpointStatus state...")
        
        check_endpoint_status = {
            "Type": "Choice",
            "Choices": [
                {
                    "Variable": "$.endpoint_status.EndpointStatus",
                    "StringEquals": "InService",
                    "Next": "ModelEvaluation"
                },
                {
                    "Variable": "$.endpoint_status.EndpointStatus",
                    "StringEquals": "Failed",
                    "Next": "DeploymentFailed"
                }
            ],
            "Default": "WaitBeforeRetry"
        }
        
        definition['States']['CheckEndpointStatus'] = check_endpoint_status
        
        # Add WaitBeforeRetry state
        print("Adding WaitBeforeRetry state...")
        
        wait_before_retry = {
            "Type": "Wait",
            "Seconds": 30,
            "Next": "WaitForEndpoint"
        }
        
        definition['States']['WaitBeforeRetry'] = wait_before_retry
        
        # Update CreateEndpoint to go to WaitForEndpoint instead of ModelEvaluation
        print("Updating CreateEndpoint next state...")
        if 'CreateEndpoint' in definition['States']:
            definition['States']['CreateEndpoint']['Next'] = 'WaitForEndpoint'
            print("[OK] CreateEndpoint now goes to WaitForEndpoint")
        
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
    print("New workflow after CreateEndpoint:")
    print("  1. CreateEndpoint (starts endpoint creation)")
    print("  2. WaitForEndpoint (describes endpoint)")
    print("  3. CheckEndpointStatus (checks if InService)")
    print("     - If InService -> ModelEvaluation")
    print("     - If Failed -> DeploymentFailed")
    print("     - Otherwise -> WaitBeforeRetry")
    print("  4. WaitBeforeRetry (wait 30 seconds)")
    print("  5. Loop back to WaitForEndpoint")
    print()
    print("This ensures endpoint is InService before evaluation runs!")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
