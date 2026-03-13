"""
Check Step Functions Execution Status

Usage:
    python check_execution_status.py --execution-arn <arn>
"""
import boto3
import json
import argparse
from datetime import datetime


def check_execution(execution_arn: str, region: str = 'us-east-1'):
    """Check the status of a Step Functions execution"""
    
    sfn = boto3.client('stepfunctions', region_name=region)
    
    print("\n" + "="*70)
    print("STEP FUNCTIONS EXECUTION STATUS")
    print("="*70 + "\n")
    
    try:
        # Get execution details
        response = sfn.describe_execution(executionArn=execution_arn)
        
        status = response['status']
        start_time = response['startDate']
        name = response['name']
        
        print(f"Execution: {name}")
        print(f"Status: {status}")
        print(f"Started: {start_time}")
        
        if 'stopDate' in response:
            stop_time = response['stopDate']
            duration = (stop_time - start_time).total_seconds()
            print(f"Stopped: {stop_time}")
            print(f"Duration: {duration:.1f} seconds")
        
        print()
        
        # Get execution history to see current state
        history = sfn.get_execution_history(
            executionArn=execution_arn,
            maxResults=50,
            reverseOrder=True
        )
        
        # Find the most recent state
        for event in history['events']:
            event_type = event['type']
            
            if event_type == 'TaskStateEntered':
                details = event.get('stateEnteredEventDetails', {})
                state_name = details.get('name', 'Unknown')
                print(f"Current State: {state_name}")
                break
            
            elif event_type == 'TaskFailed':
                details = event.get('taskFailedEventDetails', {})
                error = details.get('error', 'Unknown')
                cause = details.get('cause', 'No cause provided')
                
                print("="*70)
                print("TASK FAILED")
                print("="*70)
                print(f"\nError: {error}")
                print(f"\nCause:\n{cause}")
                print()
                break
            
            elif event_type == 'ExecutionFailed':
                details = event.get('executionFailedEventDetails', {})
                error = details.get('error', 'Unknown')
                cause = details.get('cause', 'No cause provided')
                
                print("="*70)
                print("EXECUTION FAILED")
                print("="*70)
                print(f"\nError: {error}")
                print(f"\nCause:\n{cause}")
                print()
                break
        
        # If status is FAILED, show the error
        if status == 'FAILED':
            if 'error' in response:
                print(f"Error: {response['error']}")
            if 'cause' in response:
                print(f"Cause: {response['cause']}")
        
        return status
        
    except Exception as e:
        print(f"[X] Error checking execution: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Check Step Functions execution status'
    )
    parser.add_argument(
        '--execution-arn',
        required=True,
        help='Execution ARN'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    status = check_execution(args.execution_arn, args.region)
    
    print("="*70)
    print("NEXT STEPS")
    print("="*70 + "\n")
    
    if status == 'RUNNING':
        print("The execution is still running. Check back later.")
        print("\nMonitor in AWS Console:")
        print(f"  https://console.aws.amazon.com/states/home?region={args.region}#/executions/details/{args.execution_arn}")
    
    elif status == 'FAILED':
        print("The execution failed. Review the error above.")
        print("\nCommon fixes:")
        print("  1. Check IAM permissions")
        print("  2. Verify S3 paths and files")
        print("  3. Review CloudWatch logs")
        print("  4. Fix the issue and restart:")
        print("     python start_pipeline.py --region us-east-1")
    
    elif status == 'SUCCEEDED':
        print("The execution completed successfully!")
        print("\nVerify deployment:")
        print("  python verify_deployment.py --bucket-name <bucket> --region us-east-1")
    
    print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    main()
