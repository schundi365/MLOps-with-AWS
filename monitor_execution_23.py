#!/usr/bin/env python3
"""
Monitor Execution #23 - The final push to complete deployment.

This execution should succeed with all fixes applied:
- Issue #19: Lambda numpy packaging (fixed)
- Issue #20: Lambda parameter mismatch (fixed)
- Issue #21: Workflow order (fixed)
- Issue #22: Deployment parameters (fixed)
- Issue #23: SageMaker permissions (fixed)
"""

import boto3
import time
from datetime import datetime

def main():
    region = 'us-east-1'
    execution_arn = 'arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260122-105435-205'
    
    sfn_client = boto3.client('stepfunctions', region_name=region)
    
    print("\n" + "="*70)
    print("MONITORING EXECUTION #23")
    print("="*70)
    print()
    print("This is the execution that should complete successfully!")
    print("All 23 issues have been fixed.")
    print()
    print(f"Execution ARN: {execution_arn}")
    print()
    
    last_state = None
    start_time = datetime.now()
    
    while True:
        try:
            response = sfn_client.describe_execution(executionArn=execution_arn)
            
            status = response['status']
            current_time = datetime.now()
            elapsed = (current_time - start_time).total_seconds() / 60
            
            # Get current state from history
            history = sfn_client.get_execution_history(
                executionArn=execution_arn,
                maxResults=100,
                reverseOrder=True
            )
            
            current_state = None
            for event in history['events']:
                if event['type'] == 'TaskStateEntered':
                    current_state = event['stateEnteredEventDetails']['name']
                    break
                elif event['type'] == 'PassStateEntered':
                    current_state = event['stateEnteredEventDetails']['name']
                    break
            
            if current_state != last_state:
                print(f"[{elapsed:.1f} min] State: {current_state or 'Starting...'}")
                last_state = current_state
            
            if status == 'SUCCEEDED':
                print()
                print("="*70)
                print("SUCCESS! EXECUTION #23 COMPLETED!")
                print("="*70)
                print()
                print(f"Total time: {elapsed:.1f} minutes")
                print()
                print("The pipeline has completed successfully!")
                print()
                print("Next steps:")
                print("  1. Verify deployment:")
                print("     python verify_deployment.py --bucket-name amzn-s3-movielens-327030626634 --region us-east-1")
                print()
                print("  2. Test predictions:")
                print("     python test_predictions.py")
                print()
                print("="*70)
                break
            
            elif status == 'FAILED':
                print()
                print("="*70)
                print("EXECUTION FAILED")
                print("="*70)
                print()
                
                if 'cause' in response:
                    print("Error cause:")
                    print(response['cause'])
                    print()
                
                # Get the failed state
                for event in history['events']:
                    if event['type'] == 'TaskFailed':
                        print("Failed state:", event.get('taskFailedEventDetails', {}).get('resourceType'))
                        print("Error:", event.get('taskFailedEventDetails', {}).get('error'))
                        print("Cause:", event.get('taskFailedEventDetails', {}).get('cause'))
                        break
                
                print()
                print("="*70)
                break
            
            elif status == 'TIMED_OUT':
                print()
                print("Execution timed out")
                break
            
            elif status == 'ABORTED':
                print()
                print("Execution was aborted")
                break
            
            # Wait before next check
            time.sleep(30)
            
        except KeyboardInterrupt:
            print()
            print("Monitoring stopped by user")
            print()
            print("Execution is still running. Check status with:")
            print(f"  python check_execution_status.py --execution-arn {execution_arn}")
            break
        
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    main()
