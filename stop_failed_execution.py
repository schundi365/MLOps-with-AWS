"""
Stop Failed Pipeline Execution

This script stops a failed or stuck Step Functions execution.

Usage:
    python stop_failed_execution.py --execution-arn <arn>
"""

import boto3
import argparse
from botocore.exceptions import ClientError


def stop_execution(execution_arn: str, region: str = 'us-east-1'):
    """
    Stop a Step Functions execution
    
    Args:
        execution_arn: Execution ARN to stop
        region: AWS region
        
    Returns:
        True if stopped successfully
    """
    sfn = boto3.client('stepfunctions', region_name=region)
    
    print("\n" + "="*70)
    print("STOPPING STEP FUNCTIONS EXECUTION")
    print("="*70 + "\n")
    
    print(f"Execution ARN: {execution_arn}")
    
    try:
        # First check current status
        response = sfn.describe_execution(executionArn=execution_arn)
        current_status = response['status']
        
        print(f"Current Status: {current_status}")
        
        if current_status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
            print(f"\n[!] Execution is already in terminal state: {current_status}")
            print("    No need to stop it.")
            return True
        
        # Stop the execution
        print("\n[...] Stopping execution...")
        sfn.stop_execution(
            executionArn=execution_arn,
            error='ManualStop',
            cause='Manually stopped due to duplicate job name issue'
        )
        
        print("[OK] Execution stopped successfully")
        print("\nYou can now start a new execution with:")
        print("  python start_pipeline.py --region us-east-1")
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ExecutionDoesNotExist':
            print(f"\n[X] Execution not found: {execution_arn}")
            return False
        elif e.response['Error']['Code'] == 'AccessDeniedException':
            print(f"\n[X] Access denied. You don't have permission to stop executions.")
            print("    Ask your administrator to add states:StopExecution permission.")
            print("\n    Or stop it via AWS Console:")
            print(f"    https://console.aws.amazon.com/states/home?region={region}")
            return False
        else:
            print(f"\n[X] Error stopping execution: {e}")
            return False
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Stop a failed Step Functions execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Stop specific execution
  python stop_failed_execution.py --execution-arn arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260119-155224
  
  # Stop in different region
  python stop_failed_execution.py --execution-arn <arn> --region us-west-2
        """
    )
    
    parser.add_argument(
        '--execution-arn',
        required=True,
        help='Execution ARN to stop'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    success = stop_execution(args.execution_arn, args.region)
    
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

