"""
Start pipeline execution with correct input format.
"""

import boto3
import json
from datetime import datetime

def start_pipeline():
    """Start pipeline with properly formatted input."""
    
    sfn_client = boto3.client('stepfunctions', region_name='us-east-1')
    
    # Get state machine
    state_machines = sfn_client.list_state_machines()
    
    pipeline_sm = None
    for sm in state_machines['stateMachines']:
        if 'MovieLensMLPipeline' in sm['name']:
            pipeline_sm = sm
            break
    
    if not pipeline_sm:
        print("ERROR: Could not find state machine")
        return
    
    print("\n" + "="*70)
    print("STARTING PIPELINE EXECUTION")
    print("="*70 + "\n")
    
    # Generate unique names with timestamp
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')[:20]
    
    # Prepare input with all required fields
    input_data = {
        "bucket_name": "amzn-s3-movielens-327030626634",
        "raw_data_prefix": "raw-data/",
        "processed_data_prefix": "processed-data/",
        "model_prefix": "models/",
        "embedding_dim": 128,
        "learning_rate": 0.001,
        "batch_size": 256,
        "epochs": 50,
        "instance_type": "ml.m5.xlarge",
        "instance_count": 1,
        # Add required job names
        "preprocessing_job_name": f"movielens-preprocessing-{timestamp}",
        "training_job_name": f"movielens-training-{timestamp}",
        "model_name": f"movielens-model-{timestamp}",
        "endpoint_config_name": f"movielens-endpoint-config-{timestamp}",
        "endpoint_name": f"movielens-endpoint-{timestamp}"
    }
    
    execution_name = f"execution-{timestamp}"
    
    print("Input Configuration:")
    print(json.dumps(input_data, indent=2))
    print()
    
    try:
        response = sfn_client.start_execution(
            stateMachineArn=pipeline_sm['stateMachineArn'],
            name=execution_name,
            input=json.dumps(input_data)
        )
        
        print(f"✓ Started execution: {execution_name}")
        print(f"  Execution ARN: {response['executionArn']}")
        print()
        print("Monitor progress:")
        print("  python monitor_pipeline.py --latest --follow")
        print()
        
    except Exception as e:
        print(f"ERROR starting execution: {e}")

if __name__ == '__main__':
    start_pipeline()
