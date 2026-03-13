"""
Clean up failed resources and restart pipeline with fixed inference code.
"""

import boto3
import time
from datetime import datetime

def cleanup_and_restart():
    """Clean up failed endpoint and restart pipeline."""
    
    sagemaker = boto3.client('sagemaker', region_name='us-east-1')
    sfn = boto3.client('stepfunctions', region_name='us-east-1')
    
    print("\n" + "="*70)
    print("CLEANUP AND RESTART")
    print("="*70 + "\n")
    
    # Step 1: Delete failed endpoint
    print("Step 1: Cleaning up failed endpoint...")
    
    endpoint_name = 'movielens-endpoint-20260122-162230-4567'
    
    try:
        print(f"  Deleting endpoint: {endpoint_name}")
        sagemaker.delete_endpoint(EndpointName=endpoint_name)
        print("  ✓ Endpoint deletion initiated")
    except sagemaker.exceptions.ClientError as e:
        if 'Could not find endpoint' in str(e):
            print("  ℹ Endpoint already deleted")
        else:
            print(f"  ⚠ Error deleting endpoint: {e}")
    
    # Step 2: Delete endpoint config
    print("\nStep 2: Cleaning up endpoint config...")
    
    endpoint_config_name = 'movielens-endpoint-config-20260122-162230-4567'
    
    try:
        print(f"  Deleting endpoint config: {endpoint_config_name}")
        sagemaker.delete_endpoint_config(EndpointConfigName=endpoint_config_name)
        print("  ✓ Endpoint config deleted")
    except sagemaker.exceptions.ClientError as e:
        if 'Could not find endpoint configuration' in str(e):
            print("  ℹ Endpoint config already deleted")
        else:
            print(f"  ⚠ Error deleting endpoint config: {e}")
    
    # Step 3: Delete model
    print("\nStep 3: Cleaning up model...")
    
    model_name = 'movielens-model-20260122-162230-4567'
    
    try:
        print(f"  Deleting model: {model_name}")
        sagemaker.delete_model(ModelName=model_name)
        print("  ✓ Model deleted")
    except sagemaker.exceptions.ClientError as e:
        if 'Could not find model' in str(e):
            print("  ℹ Model already deleted")
        else:
            print(f"  ⚠ Error deleting model: {e}")
    
    print("\n" + "="*70)
    print("STARTING NEW PIPELINE EXECUTION")
    print("="*70 + "\n")
    
    # Get state machine ARN
    state_machines = sfn.list_state_machines()
    pipeline_sm = None
    
    for sm in state_machines['stateMachines']:
        if 'MovieLensMLPipeline' in sm['name']:
            pipeline_sm = sm
            break
    
    if not pipeline_sm:
        print("ERROR: Could not find MovieLensMLPipeline state machine")
        return
    
    print(f"State Machine: {pipeline_sm['name']}")
    print(f"ARN: {pipeline_sm['stateMachineArn']}")
    print()
    
    # Create execution name with timestamp
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    execution_name = f"execution-{timestamp}-final"
    
    # Start execution with proper input (all required fields)
    input_data = {
        "bucket_name": "amzn-s3-movielens-327030626634",
        "raw_data_prefix": "raw-data/ml-100k",
        "processed_data_prefix": "processed-data",
        "models_prefix": "models",
        "timestamp": timestamp,
        "preprocessing_job_name": f"movielens-preprocessing-{timestamp}",
        "training_job_name": f"movielens-training-{timestamp}",
        "model_name": f"movielens-model-{timestamp}",
        "endpoint_config_name": f"movielens-endpoint-config-{timestamp}",
        "endpoint_name": f"movielens-endpoint-{timestamp}"
    }
    
    print("Starting execution with input:")
    import json
    print(json.dumps(input_data, indent=2))
    print()
    
    try:
        response = sfn.start_execution(
            stateMachineArn=pipeline_sm['stateMachineArn'],
            name=execution_name,
            input=json.dumps(input_data)
        )
        
        print("✓ Execution started successfully!")
        print()
        print(f"Execution ARN: {response['executionArn']}")
        print(f"Execution Name: {execution_name}")
        print(f"Start Time: {response['startDate']}")
        print()
        
    except Exception as e:
        print(f"ERROR starting execution: {e}")
        return
    
    print("="*70)
    print("MONITORING")
    print("="*70)
    print()
    print("The pipeline is now running with the FIXED inference code.")
    print()
    print("What's different this time:")
    print("  ✓ sourcedir.tar.gz now contains inference.py and model.py")
    print("  ✓ Training script will copy these into model artifacts")
    print("  ✓ Endpoint will use custom inference handler")
    print()
    print("To monitor progress:")
    print(f"  python monitor_pipeline.py")
    print()
    print("Or check the AWS Console:")
    print(f"  https://console.aws.amazon.com/states/home?region=us-east-1#/executions/details/{response['executionArn']}")
    print()
    print("Expected timeline:")
    print("  - Data Preprocessing: ~2-3 minutes")
    print("  - Model Training: ~30-45 minutes")
    print("  - Model Deployment: ~5-10 minutes")
    print("  - Model Evaluation: ~1-2 minutes")
    print("  - Total: ~40-60 minutes")
    print()

if __name__ == '__main__':
    cleanup_and_restart()
