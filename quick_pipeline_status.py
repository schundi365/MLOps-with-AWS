"""
Quick pipeline status check without continuous monitoring.
"""

import boto3
from datetime import datetime, timezone

def quick_status():
    """Get current pipeline status."""
    
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
    
    # Get latest execution
    executions = sfn_client.list_executions(
        stateMachineArn=pipeline_sm['stateMachineArn'],
        maxResults=1
    )
    
    if not executions['executions']:
        print("No executions found")
        return
    
    execution = executions['executions'][0]
    execution_arn = execution['executionArn']
    
    # Get detailed execution info
    details = sfn_client.describe_execution(executionArn=execution_arn)
    
    # Calculate elapsed time
    start_time = details['startDate']
    now = datetime.now(timezone.utc)
    elapsed = now - start_time
    
    print("\n" + "="*70)
    print("PIPELINE STATUS")
    print("="*70 + "\n")
    
    print(f"Execution: {execution['name']}")
    print(f"Status: {execution['status']}")
    print(f"Started: {start_time}")
    print(f"Elapsed: {elapsed}")
    
    # Get recent events
    history = sfn_client.get_execution_history(
        executionArn=execution_arn,
        reverseOrder=True,
        maxResults=10
    )
    
    print("\nRecent Events:")
    for event in history['events']:
        event_type = event['type']
        timestamp = event['timestamp']
        
        if 'StateEntered' in event_type:
            state_name = event['stateEnteredEventDetails']['name']
            print(f"  [{timestamp}] Entered: {state_name}")
        elif 'StateExited' in event_type:
            state_name = event['stateExitedEventDetails']['name']
            print(f"  [{timestamp}] Completed: {state_name}")
        elif 'Failed' in event_type:
            print(f"  [{timestamp}] FAILED: {event_type}")
    
    print("\n" + "="*70 + "\n")
    
    if execution['status'] == 'RUNNING':
        print("✓ Pipeline is running normally")
        print("\nExpected timeline:")
        print("  - Data Preprocessing: ~5-10 minutes")
        print("  - Model Training: ~30-45 minutes")
        print("  - Model Evaluation: ~2-5 minutes")
        print("  - Model Deployment: ~5-10 minutes")
        print("  - Monitoring Setup: ~1-2 minutes")
    elif execution['status'] == 'SUCCEEDED':
        print("✓ Pipeline completed successfully!")
    elif execution['status'] == 'FAILED':
        print("✗ Pipeline failed - check logs for details")
    
    print()

if __name__ == '__main__':
    quick_status()
