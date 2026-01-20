#!/usr/bin/env python3
"""
Quick status checker for the current pipeline execution.
Run this periodically to see progress.
"""

import boto3
from datetime import datetime

def main():
    # Configuration
    execution_arn = "arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260120-172341-720"
    region = "us-east-1"
    
    # Create client
    sfn = boto3.client('stepfunctions', region_name=region)
    
    try:
        # Get execution details
        response = sfn.describe_execution(executionArn=execution_arn)
        
        status = response['status']
        start_time = response['startDate']
        current_time = datetime.now(start_time.tzinfo)
        elapsed = (current_time - start_time).total_seconds() / 60
        
        print("\n" + "="*70)
        print("QUICK STATUS CHECK")
        print("="*70)
        print(f"Status: {status}")
        print(f"Started: {start_time.strftime('%H:%M:%S')} UTC")
        print(f"Elapsed: {elapsed:.1f} minutes")
        print(f"Current Time: {current_time.strftime('%H:%M:%S')} UTC")
        
        if status == 'RUNNING':
            # Try to get current state
            try:
                history = sfn.get_execution_history(
                    executionArn=execution_arn,
                    maxResults=10,
                    reverseOrder=True
                )
                
                for event in history['events']:
                    if event['type'] == 'TaskStateEntered':
                        state_name = event.get('stateEnteredEventDetails', {}).get('name', 'Unknown')
                        print(f"Current Phase: {state_name}")
                        break
            except:
                pass
            
            # Estimate completion
            if elapsed < 10:
                print("\nPhase: Data Preprocessing")
                print("Expected: ~10 minutes")
                remaining = 10 - elapsed
            elif elapsed < 55:
                print("\nPhase: Model Training")
                print("Expected: ~45 minutes")
                remaining = 55 - elapsed
            elif elapsed < 60:
                print("\nPhase: Model Evaluation")
                print("Expected: ~5 minutes")
                remaining = 60 - elapsed
            elif elapsed < 70:
                print("\nPhase: Model Deployment")
                print("Expected: ~10 minutes")
                remaining = 70 - elapsed
            else:
                print("\nPhase: Monitoring Setup")
                print("Expected: ~2 minutes")
                remaining = 72 - elapsed
            
            if remaining > 0:
                print(f"Estimated remaining: {remaining:.1f} minutes")
                completion_time = current_time.replace(
                    minute=current_time.minute + int(remaining),
                    second=current_time.second
                )
                print(f"Expected completion: ~{completion_time.strftime('%H:%M')} UTC")
            else:
                print("Should complete soon!")
            
            print("\nCheck again in 5-10 minutes")
            
        elif status == 'SUCCEEDED':
            end_time = response.get('stopDate')
            total_time = (end_time - start_time).total_seconds() / 60
            print(f"\n*** SUCCESS! ***")
            print(f"Completed: {end_time.strftime('%H:%M:%S')} UTC")
            print(f"Total time: {total_time:.1f} minutes")
            print("\nNext steps:")
            print("1. Run: python verify_deployment.py --bucket-name amzn-s3-movielens-327030626634 --region us-east-1")
            print("2. Test predictions on the endpoint")
            print("3. Review CloudWatch dashboard")
            
        elif status == 'FAILED':
            print(f"\n*** FAILED ***")
            if 'error' in response:
                print(f"Error: {response['error']}")
            if 'cause' in response:
                print(f"Cause: {response['cause'][:200]}...")
            print("\nCheck CloudWatch logs for details")
            
        print("="*70)
        print()
        
    except Exception as e:
        print(f"\nError checking status: {e}")
        print("\nMake sure you have AWS credentials configured.")
        print("Run: aws configure")

if __name__ == "__main__":
    main()
