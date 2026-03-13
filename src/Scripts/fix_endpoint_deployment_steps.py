#!/usr/bin/env python3
"""
Fix Issue #22: Missing endpoint configuration.

Problem: Step Functions tries to create endpoint with a configuration that doesn't exist.
The workflow is missing steps to create the model and endpoint configuration.

Solution: Add CreateModel and CreateEndpointConfig steps before CreateEndpoint.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #22: Missing Endpoint Configuration")
    print("="*70)
    print()
    
    print("Problem: Endpoint configuration doesn't exist")
    print("Current: ModelTraining → CreateEndpoint (missing config!)")
    print("Fixed: ModelTraining → CreateModel → CreateEndpointConfig → CreateEndpoint")
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
        sagemaker_role_arn = f"arn:aws:iam::{account_id}:role/MovieLensSageMakerRole"
        
        print("[OK] State machine fetched")
        print()
        
        # Add CreateModel step
        print("Adding CreateModel step...")
        definition['States']['CreateModel'] = {
            "Type": "Task",
            "Resource": "arn:aws:states:::sagemaker:createModel",
            "Parameters": {
                "ModelName.$": "$.model_name",
                "PrimaryContainer": {
                    "Image": f"763104351884.dkr.ecr.{region}.amazonaws.com/pytorch-inference:2.0.0-cpu-py310",
                    "ModelDataUrl.$": "$.ModelArtifacts.S3ModelArtifacts"
                },
                "ExecutionRoleArn": sagemaker_role_arn
            },
            "ResultPath": "$.model_result",
            "Next": "CreateEndpointConfig",
            "Retry": [
                {
                    "ErrorEquals": ["States.TaskFailed"],
                    "IntervalSeconds": 30,
                    "MaxAttempts": 2,
                    "BackoffRate": 2.0
                }
            ],
            "Catch": [
                {
                    "ErrorEquals": ["States.ALL"],
                    "Next": "DeploymentFailed"
                }
            ]
        }
        print("[OK] CreateModel step added")
        
        # Add CreateEndpointConfig step
        print("Adding CreateEndpointConfig step...")
        definition['States']['CreateEndpointConfig'] = {
            "Type": "Task",
            "Resource": "arn:aws:states:::sagemaker:createEndpointConfig",
            "Parameters": {
                "EndpointConfigName.$": "$.endpoint_config_name",
                "ProductionVariants": [
                    {
                        "VariantName": "AllTraffic",
                        "ModelName.$": "$.model_name",
                        "InitialInstanceCount": 1,
                        "InstanceType": "ml.m5.xlarge"
                    }
                ]
            },
            "ResultPath": "$.endpoint_config_result",
            "Next": "CreateEndpoint",
            "Retry": [
                {
                    "ErrorEquals": ["States.TaskFailed"],
                    "IntervalSeconds": 30,
                    "MaxAttempts": 2,
                    "BackoffRate": 2.0
                }
            ],
            "Catch": [
                {
                    "ErrorEquals": ["States.ALL"],
                    "Next": "DeploymentFailed"
                }
            ]
        }
        print("[OK] CreateEndpointConfig step added")
        
        # Rename ModelDeployment to CreateEndpoint for clarity
        print("Updating CreateEndpoint step...")
        definition['States']['CreateEndpoint'] = definition['States']['ModelDeployment']
        # Remove static EndpointName if it exists
        if 'EndpointName' in definition['States']['CreateEndpoint']['Parameters']:
            del definition['States']['CreateEndpoint']['Parameters']['EndpointName']
        # Add dynamic EndpointName
        definition['States']['CreateEndpoint']['Parameters']['EndpointName.$'] = "$.endpoint_name"
        del definition['States']['ModelDeployment']
        print("[OK] CreateEndpoint step updated")
        
        # Update ModelTraining to go to CreateModel
        definition['States']['ModelTraining']['Next'] = 'CreateModel'
        print("[OK] ModelTraining now goes to CreateModel")
        
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
    print("New deployment workflow:")
    print("  1. ModelTraining")
    print("  2. CreateModel          <- NEW!")
    print("  3. CreateEndpointConfig <- NEW!")
    print("  4. CreateEndpoint       <- Now has config!")
    print("  5. ModelEvaluation")
    print("  6. CheckEvaluationResult")
    print("  7. MonitoringSetup")
    print()
    print("Now the endpoint configuration will exist!")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
