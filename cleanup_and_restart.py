"""
Clean up failed endpoint and restart pipeline execution.
"""

import boto3
import time

def cleanup_and_restart():
    """Clean up failed resources and start fresh execution."""
    
    sagemaker_client = boto3.client('sagemaker', region_name='us-east-1')
    sfn_client = boto3.client('stepfunctions', region_name='us-east-1')
    
    print("\n" + "="*70)
    print("CLEANUP AND RESTART")
    print("="*70 + "\n")
    
    # Step 1: Delete failed endpoint
    print("Step 1: Cleaning up failed endpoint...")
    
    failed_endpoint = 'movielens-endpoint-20260122-155327-140'
    
    try:
        sagemaker_client.delete_endpoint(EndpointName=failed_endpoint)
        print(f"  ✓ Deleted endpoint: {failed_endpoint}")
    except sagemaker_client.exceptions.ClientError as e:
        if 'Could not find endpoint' in str(e):
            print(f"  ℹ Endpoint already deleted: {failed_endpoint}")
        else:
            print(f"  ⚠ Error deleting endpoint: {e}")
    
    # Wait a moment for cleanup
    time.sleep(2)
    
    # Step 2: Stop any running executions
    print("\nStep 2: Checking for running executions...")
    
    state_machines = sfn_client.list_state_machines()
    pipeline_sm = None
    
    for sm in state_machines['stateMachines']:
        if 'MovieLensMLPipeline' in sm['name']:
            pipeline_sm = sm
            break
    
    if not pipeline_sm:
        print("  ERROR: Could not find state machine")
        return
    
    # List running executions
    executions = sfn_client.list_executions(
        stateMachineArn=pipeline_sm['stateMachineArn'],
        statusFilter='RUNNING'
    )
    
    if executions['executions']:
        print(f"  Found {len(executions['executions'])} running execution(s)")
        for execution in executions['executions']:
            try:
                sfn_client.stop_execution(
                    executionArn=execution['executionArn'],
                    error='ManualStop',
                    cause='Stopping to restart with fixed inference configuration'
                )
                print(f"  ✓ Stopped: {execution['name']}")
            except Exception as e:
                print(f"  ⚠ Error stopping execution: {e}")
    else:
        print("  ℹ No running executions found")
    
    # Step 3: Start new execution
    print("\nStep 3: Starting new pipeline execution...")
    
    import json
    from datetime import datetime
    
    execution_name = f"execution-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
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
        "instance_count": 1
    }
    
    try:
        response = sfn_client.start_execution(
            stateMachineArn=pipeline_sm['stateMachineArn'],
            name=execution_name,
            input=json.dumps(input_data)
        )
        
        print(f"  ✓ Started execution: {execution_name}")
        print(f"  Execution ARN: {response['executionArn']}")
        
    except Exception as e:
        print(f"  ERROR starting execution: {e}")
        return
    
    print("\n" + "="*70)
    print("SUCCESS")
    print("="*70)
    print(f"\nNew execution started: {execution_name}")
    print("\nMonitor progress:")
    print("  python monitor_pipeline.py")
    print("\nOr check in AWS Console:")
    print(f"  https://console.aws.amazon.com/states/home?region=us-east-1#/executions/details/{response['executionArn']}")
    print()

if __name__ == '__main__':
    cleanup_and_restart()
