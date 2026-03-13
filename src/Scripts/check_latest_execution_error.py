"""
Check the error details from the latest execution.
"""

import boto3
import json

def check_latest_error():
    """Get detailed error from latest execution."""
    
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
    
    execution_arn = executions['executions'][0]['executionArn']
    
    # Get execution details
    execution = sfn_client.describe_execution(executionArn=execution_arn)
    
    print("\n" + "="*70)
    print("EXECUTION ERROR DETAILS")
    print("="*70 + "\n")
    
    print(f"Execution: {executions['executions'][0]['name']}")
    print(f"Status: {execution['status']}")
    print(f"Started: {execution['startDate']}")
    
    if 'stopDate' in execution:
        print(f"Stopped: {execution['stopDate']}")
    
    # Get execution history
    history = sfn_client.get_execution_history(
        executionArn=execution_arn,
        reverseOrder=True,
        maxResults=50
    )
    
    print("\n" + "-"*70)
    print("ERROR EVENTS")
    print("-"*70 + "\n")
    
    for event in history['events']:
        event_type = event['type']
        
        if 'Failed' in event_type or 'Error' in event_type:
            print(f"Event Type: {event_type}")
            print(f"Timestamp: {event['timestamp']}")
            
            # Print relevant details
            for key, value in event.items():
                if key not in ['type', 'timestamp', 'id', 'previousEventId']:
                    if isinstance(value, dict):
                        print(f"\n{key}:")
                        print(json.dumps(value, indent=2))
                    else:
                        print(f"{key}: {value}")
            
            print("\n" + "-"*70 + "\n")

if __name__ == '__main__':
    check_latest_error()
