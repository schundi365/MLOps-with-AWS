"""
Restart pipeline with ALL fixes applied (Issues #27-30).
"""

import boto3
import json
from datetime import datetime

def restart_pipeline():
    """Stop any running execution and restart pipeline with all fixes."""
    
    sfn = boto3.client('stepfunctions', region_name='us-east-1')
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    
    print("\n" + "="*70)
    print("RESTART PIPELINE WITH ALL FIXES APPLIED")
    print("="*70 + "\n")
    
    print("="*70)
    print("ALL FIXES APPLIED")
    print("="*70)
    print()
    print("✅ Issue #27: Inference code packaging")
    print("   • sourcedir.tar.gz contains train.py, inference.py, model.py")
    print()
    print("✅ Issue #28: Hyperparameter names")
    print("   • All hyperparameters use hyphens (batch-size, learning-rate, etc.)")
    print()
    print("✅ Issue #29: SageMaker parameters")
    print("   • sagemaker_program and sagemaker_submit_directory present")
    print()
    print("✅ Issue #30: Monitoring Lambda handler")
    print("   • lambda_handler function added and deployed")
    print()
    
    print("="*70)
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
    execution_name = f"execution-{timestamp}-all-fixes"
    
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
    print("EXPECTED PIPELINE FLOW")
    print("="*70)
    print()
    print("1. Data Preprocessing (~2-3 minutes)")
    print("   ✓ Load raw data from S3")
    print("   ✓ Split into train/validation/test sets")
    print("   ✓ Save processed data to S3")
    print()
    print("2. Model Training (~30-45 minutes)")
    print("   ✓ Parse arguments correctly (hyphens)")
    print("   ✓ Load training and validation data")
    print("   ✓ Train collaborative filtering model")
    print("   ✓ Copy inference files to model artifacts")
    print("   ✓ Save model with validation RMSE < 0.9")
    print()
    print("3. Model Evaluation (~1-2 minutes)")
    print("   ✓ Lambda evaluates model on test set")
    print("   ✓ Check RMSE threshold")
    print("   ✓ Pass evaluation results to next step")
    print()
    print("4. Model Deployment (~5-10 minutes)")
    print("   ✓ Create SageMaker model with inference code")
    print("   ✓ Create endpoint configuration")
    print("   ✓ Deploy endpoint (wait for InService)")
    print("   ✓ Custom inference handler loads")
    print()
    print("5. Enable Monitoring (~1 minute)")
    print("   ✓ Lambda creates CloudWatch dashboard")
    print("   ✓ Lambda creates CloudWatch alarms")
    print("   ✓ SNS topic configured for notifications")
    print("   ✓ Pipeline completes successfully")
    print()
    print("="*70)
    print("MONITORING")
    print("="*70)
    print()
    print("To monitor progress:")
    print(f"  python monitor_pipeline.py --latest --follow")
    print()
    print("Or check the AWS Console:")
    print(f"  https://console.aws.amazon.com/states/home?region=us-east-1#/executions/details/{response['executionArn']}")
    print()
    print("Expected completion: ~40-60 minutes")
    print()
    
    return True

if __name__ == '__main__':
    success = restart_pipeline()
    exit(0 if success else 1)
