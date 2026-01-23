#!/usr/bin/env python3
"""
Check detailed execution history for Execution #23.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    execution_arn = 'arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260122-105435-205'
    
    sfn_client = boto3.client('stepfunctions', region_name=region)
    
    print("\n" + "="*70)
    print("EXECUTION #23 DETAILED HISTORY")
    print("="*70)
    print()
    
    # Get execution details
    response = sfn_client.describe_execution(executionArn=execution_arn)
    
    print(f"Status: {response['status']}")
    print(f"Started: {response['startDate']}")
    print(f"Stopped: {response.get('stopDate', 'N/A')}")
    print()
    
    if 'cause' in response:
        print("Cause:")
        print(response['cause'])
        print()
    
    # Get execution history
    print("="*70)
    print("EXECUTION HISTORY (Most Recent Events)")
    print("="*70)
    print()
    
    history = sfn_client.get_execution_history(
        executionArn=execution_arn,
        maxResults=50,
        reverseOrder=True
    )
    
    for event in history['events']:
        event_type = event['type']
        timestamp = event['timestamp']
        
        if event_type == 'ExecutionFailed':
            print(f"[{timestamp}] EXECUTION FAILED")
            details = event.get('executionFailedEventDetails', {})
            print(f"  Error: {details.get('error', 'N/A')}")
            print(f"  Cause: {details.get('cause', 'N/A')}")
            print()
        
        elif event_type == 'TaskFailed':
            print(f"[{timestamp}] TASK FAILED")
            details = event.get('taskFailedEventDetails', {})
            print(f"  Resource: {details.get('resourceType', 'N/A')}")
            print(f"  Error: {details.get('error', 'N/A')}")
            cause = details.get('cause', 'N/A')
            if len(cause) > 500:
                print(f"  Cause: {cause[:500]}...")
            else:
                print(f"  Cause: {cause}")
            print()
        
        elif event_type == 'LambdaFunctionFailed':
            print(f"[{timestamp}] LAMBDA FAILED")
            details = event.get('lambdaFunctionFailedEventDetails', {})
            print(f"  Error: {details.get('error', 'N/A')}")
            print(f"  Cause: {details.get('cause', 'N/A')}")
            print()
        
        elif event_type == 'TaskStateEntered':
            details = event.get('stateEnteredEventDetails', {})
            state_name = details.get('name', 'Unknown')
            print(f"[{timestamp}] Entered state: {state_name}")
        
        elif event_type == 'TaskSucceeded':
            print(f"[{timestamp}] Task succeeded")
        
        elif event_type == 'TaskStateExited':
            details = event.get('stateExitedEventDetails', {})
            state_name = details.get('name', 'Unknown')
            print(f"[{timestamp}] Exited state: {state_name}")
    
    print()
    print("="*70)

if __name__ == "__main__":
    main()
