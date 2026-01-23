#!/usr/bin/env python3
"""
Fix Issue #22: Deployment missing model_name and other parameters.

Problem: The CreateModel state expects $.model_name but it's not in the state.
After training, we need to add model_name, model_data, and endpoint_config_name.

Solution: Add a Pass state after training to construct these values, then
update CreateModel, CreateEndpointConfig, and CreateEndpoint to use them.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #22: Deployment Missing Parameters")
    print("="*70)
    print()
    
    print("Problem: CreateModel expects $.model_name but it's not in state")
    print("Solution: Add Pass state to construct deployment parameters")
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
        sagemaker_role_arn = "arn:aws:iam::327030626634:role/MovieLensSageMakerRole"
        
        print("[OK] State machine fetched")
        print()
        
        # Add PrepareDeployment Pass state after ModelTraining
        print("Adding PrepareDeployment state...")
        
        prepare_deployment = {
            "Type": "Pass",
            "Comment": "Prepare deployment parameters from training output",
            "Parameters": {
                "preprocessing_job_name.$": "$.preprocessing_job_name",
                "training_job_name.$": "$.training_job_name",
                "endpoint_name.$": "$.endpoint_name",
                "model_name.$": "$.training_job_name",  # Use training job name as model name
                "endpoint_config_name.$": "States.Format('{}-config', $.training_job_name)",
                "model_data.$": "$.training_result.ModelArtifacts.S3ModelArtifacts"
            },
            "Next": "CreateModel"
        }
        
        definition['States']['PrepareDeployment'] = prepare_deployment
        
        # Update ModelTraining to go to PrepareDeployment
        definition['States']['ModelTraining']['Next'] = 'PrepareDeployment'
        
        print("[OK] PrepareDeployment state added")
        
        # Update or create CreateModel state
        print("Updating CreateModel state...")
        
        create_model = {
            "Type": "Task",
            "Resource": "arn:aws:states:::sagemaker:createModel",
            "Parameters": {
                "ModelName.$": "$.model_name",
                "PrimaryContainer": {
                    "Image": f"763104351884.dkr.ecr.{region}.amazonaws.com/pytorch-inference:2.0.0-cpu-py310",
                    "ModelDataUrl.$": "$.model_data"
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
        
        definition['States']['CreateModel'] = create_model
        
        print("[OK] CreateModel state updated")
        
        # Add CreateEndpointConfig state
        print("Adding CreateEndpointConfig state...")
        
        create_endpoint_config = {
            "Type": "Task",
            "Resource": "arn:aws:states:::sagemaker:createEndpointConfig",
            "Parameters": {
                "EndpointConfigName.$": "$.endpoint_config_name",
                "ProductionVariants": [
                    {
                        "VariantName": "AllTraffic",
                        "ModelName.$": "$.model_name",
                        "InitialInstanceCount": 1,
                        "InstanceType": "ml.m5.xlarge",
                        "InitialVariantWeight": 1.0
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
        
        definition['States']['CreateEndpointConfig'] = create_endpoint_config
        
        print("[OK] CreateEndpointConfig state added")
        
        # Add CreateEndpoint state
        print("Adding CreateEndpoint state...")
        
        create_endpoint = {
            "Type": "Task",
            "Resource": "arn:aws:states:::sagemaker:createEndpoint",
            "Parameters": {
                "EndpointName.$": "$.endpoint_name",
                "EndpointConfigName.$": "$.endpoint_config_name"
            },
            "ResultPath": "$.endpoint_result",
            "Next": "ModelEvaluation",
            "Retry": [
                {
                    "ErrorEquals": ["States.TaskFailed"],
                    "IntervalSeconds": 60,
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
        
        definition['States']['CreateEndpoint'] = create_endpoint
        
        print("[OK] CreateEndpoint state added")
        
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
    print("  2. PrepareDeployment    <- NEW (constructs parameters)")
    print("  3. CreateModel          <- FIXED (uses $.model_name)")
    print("  4. CreateEndpointConfig <- NEW")
    print("  5. CreateEndpoint       <- NEW")
    print("  6. ModelEvaluation")
    print("  7. CheckEvaluationResult")
    print("  8. MonitoringSetup")
    print()
    print("All deployment parameters are now properly constructed!")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
