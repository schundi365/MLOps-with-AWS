"""
Restart pipeline with complete fix (hyperparameters + SageMaker parameters).
"""

import boto3
import json
from datetime import datetime

def restart_pipeline():
    """Stop failed execution and restart pipeline."""
    
    sagemaker = boto3.client('sagemaker', region_name='us-east-1')
    sfn = boto3.client('stepfunctions', region_name='us-east-1')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    
    print("\n" + "="*70)
    print("RESTART PIPELINE WITH COMPLETE FIX")
    print("="*70 + "\n")
    
    # Step 1: Stop failed execution
    print("Step 1: Stopping failed execution...")
    execution_name = 'execution-20260123-114011-hyphen-fix'
    execution_arn = f"arn:aws:states:us-east-1:{account_id}:execution:MovieLensMLPipeline:{execution_name}"
    
    try:
        response = sfn.describe_execution(executionArn=execution_arn)
        status = response['status']
        
        if status == 'RUNNING':
            print(f"  Execution status: {status}")
            print(f"  Stopping execution: {execution_name}")
            sfn.stop_execution(
                executionArn=execution_arn,
                error='ManualStop',
                cause='Stopping to restart with complete fix'
            )
            print("  ✓ Execution stop initiated")
        else:
            print(f"  Execution already in terminal state: {status}")
    except Exception as e:
        print(f"  ℹ Execution not found or already stopped: {e}")
    
    print("\n" + "="*70)
    print("STARTING NEW PIPELINE EXECUTION")
    print("="*70 + "\n")
    
    # Get state machine ARN
    state_machine_name = 'MovieLensMLPipeline'
    state_machine_arn = f"arn:aws:states:us-east-1:{account_id}:stateMachine:{state_machine_name}"
    
    print(f"State Machine: {state_machine_name}")
    print(f"ARN: {state_machine_arn}")
    print()
    
    # Create execution name with timestamp
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    execution_name = f"execution-{timestamp}-complete-fix"
    
    # Start execution with proper input
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
    print(json.dumps(input_data, indent=2))
    print()
    
    try:
        response = sfn.start_execution(
            stateMachineArn=state_machine_arn,
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
        return False
    
    print("="*70)
    print("WHAT'S FIXED THIS TIME")
    print("="*70)
    print()
    print("✓ Hyperparameter names use hyphens:")
    print("  • batch-size, learning-rate, embedding-dim, num-factors")
    print()
    print("✓ SageMaker parameters added:")
    print("  • sagemaker_program: train.py")
    print("  • sagemaker_submit_directory: s3://.../sourcedir.tar.gz")
    print()
    print("✓ sourcedir.tar.gz contains all files:")
    print("  • train.py, inference.py, model.py")
    print()
    print("="*70)
    print("MONITORING")
    print("="*70)
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
    print("  - Model Evaluation: ~1-2 minutes")
    print("  - Model Deployment: ~5-10 minutes")
    print("  - Total: ~40-60 minutes")
    print()
    
    return True

if __name__ == '__main__':
    success = restart_pipeline()
    exit(0 if success else 1)
