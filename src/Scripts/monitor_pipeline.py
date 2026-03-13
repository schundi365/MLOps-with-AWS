"""
Monitor ML Pipeline Execution

This script monitors the progress of a running ML pipeline execution.

Usage:
    python monitor_pipeline.py --execution-arn <arn>
    python monitor_pipeline.py --latest
"""

import boto3
import argparse
import time
from datetime import datetime
from botocore.exceptions import ClientError


def get_latest_execution(region: str) -> str:
    """Get the ARN of the latest execution"""
    sfn = boto3.client('stepfunctions', region_name=region)
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:MovieLensMLPipeline"
    
    try:
        response = sfn.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=1,
            statusFilter='RUNNING'
        )
        
        if response['executions']:
            return response['executions'][0]['executionArn']
        
        # If no running, get latest
        response = sfn.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=1
        )
        
        if response['executions']:
            return response['executions'][0]['executionArn']
        
        return None
        
    except ClientError as e:
        print(f"[X] Error finding execution: {e}")
        return None


def monitor_execution(execution_arn: str, region: str, follow: bool = False):
    """
    Monitor pipeline execution
    
    Args:
        execution_arn: Execution ARN to monitor
        region: AWS region
        follow: If True, continuously monitor until completion
    """
    sfn = boto3.client('stepfunctions', region_name=region)
    
    try:
        while True:
            # Get execution details
            response = sfn.describe_execution(executionArn=execution_arn)
            
            status = response['status']
            start_time = response['startDate']
            
            # Calculate elapsed time
            elapsed = datetime.now(start_time.tzinfo) - start_time
            elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds
            
            # Clear screen (optional)
            print("\n" + "="*70)
            print("ML PIPELINE EXECUTION STATUS")
            print("="*70 + "\n")
            
            print(f"Execution ARN: {execution_arn}")
            print(f"Status: {status}")
            print(f"Started: {start_time}")
            print(f"Elapsed Time: {elapsed_str}")
            
            if status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                stop_time = response.get('stopDate')
                if stop_time:
                    duration = stop_time - start_time
                    duration_str = str(duration).split('.')[0]
                    print(f"Stopped: {stop_time}")
                    print(f"Total Duration: {duration_str}")
            
            # Get execution history to show current step
            history = sfn.get_execution_history(
                executionArn=execution_arn,
                maxResults=10,
                reverseOrder=True
            )
            
            print("\n" + "-"*70)
            print("RECENT EVENTS")
            print("-"*70 + "\n")
            
            for event in history['events'][:5]:
                event_type = event['type']
                timestamp = event['timestamp']
                
                # Format event details
                if event_type == 'TaskStateEntered':
                    details = event.get('stateEnteredEventDetails', {})
                    state_name = details.get('name', 'Unknown')
                    print(f"[{timestamp}] Entered: {state_name}")
                
                elif event_type == 'TaskStateExited':
                    details = event.get('stateExitedEventDetails', {})
                    state_name = details.get('name', 'Unknown')
                    print(f"[{timestamp}] Completed: {state_name}")
                
                elif event_type == 'TaskFailed':
                    details = event.get('taskFailedEventDetails', {})
                    error = details.get('error', 'Unknown')
                    cause = details.get('cause', 'Unknown')
                    print(f"[{timestamp}] FAILED: {error}")
                    print(f"  Cause: {cause}")
                
                elif event_type == 'ExecutionSucceeded':
                    print(f"[{timestamp}] EXECUTION SUCCEEDED!")
                
                elif event_type == 'ExecutionFailed':
                    print(f"[{timestamp}] EXECUTION FAILED!")
            
            # Show status-specific information
            print("\n" + "-"*70)
            
            if status == 'RUNNING':
                print("STATUS: Pipeline is running...")
                print("\nExpected steps:")
                print("  1. [~5-10 min]  Data Preprocessing")
                print("  2. [~30-45 min] Model Training")
                print("  3. [~2-5 min]   Model Evaluation")
                print("  4. [~5-10 min]  Model Deployment")
                print("  5. [~1-2 min]   Monitoring Setup")
                
            elif status == 'SUCCEEDED':
                print("STATUS: Pipeline completed successfully!")
                print("\nNext steps:")
                print("  1. Verify deployment:")
                print("     python verify_deployment.py --bucket-name <bucket> --region us-east-1")
                print("  2. View metrics in CloudWatch Dashboard")
                print("  3. Test endpoint predictions")
                
            elif status == 'FAILED':
                print("STATUS: Pipeline failed!")
                print("\nTroubleshooting:")
                print("  1. Check CloudWatch Logs for detailed errors")
                print("  2. Review Step Functions execution in AWS Console")
                print("  3. Verify data format in S3")
                
            elif status == 'TIMED_OUT':
                print("STATUS: Pipeline timed out!")
                print("\nThis usually means training took too long.")
                print("Consider using a larger instance type or reducing data size.")
                
            elif status == 'ABORTED':
                print("STATUS: Pipeline was manually stopped")
            
            print("\n" + "="*70)
            
            # If not following or execution is complete, break
            if not follow or status in ['SUCCEEDED', 'FAILED', 'TIMED_OUT', 'ABORTED']:
                break
            
            # Wait before next check
            print("\nRefreshing in 30 seconds... (Ctrl+C to stop)")
            time.sleep(30)
            
    except ClientError as e:
        print(f"\n[X] Error monitoring execution: {e}")
    except KeyboardInterrupt:
        print("\n\n[!] Monitoring stopped by user")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Monitor MovieLens ML pipeline execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor specific execution
  python monitor_pipeline.py --execution-arn arn:aws:states:...
  
  # Monitor latest execution
  python monitor_pipeline.py --latest --region us-east-1
  
  # Continuously monitor until completion
  python monitor_pipeline.py --latest --follow
        """
    )
    
    parser.add_argument(
        '--execution-arn',
        help='Execution ARN to monitor'
    )
    parser.add_argument(
        '--latest',
        action='store_true',
        help='Monitor the latest execution'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--follow',
        action='store_true',
        help='Continuously monitor until completion'
    )
    
    args = parser.parse_args()
    
    # Determine execution ARN
    if args.execution_arn:
        execution_arn = args.execution_arn
    elif args.latest:
        print("Finding latest execution...")
        execution_arn = get_latest_execution(args.region)
        if not execution_arn:
            print("[X] No executions found")
            print("    Start a pipeline first: python start_pipeline.py")
            return 1
    else:
        print("[X] Must specify either --execution-arn or --latest")
        parser.print_help()
        return 1
    
    # Monitor execution
    monitor_execution(execution_arn, args.region, args.follow)
    
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
