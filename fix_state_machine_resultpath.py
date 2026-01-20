"""
Fix State Machine ResultPath Configuration

This script updates the Step Functions state machine to properly pass
input parameters between states using ResultPath.

Usage:
    python fix_state_machine_resultpath.py --bucket amzn-s3-movielens-327030626634
"""

import boto3
import json
import argparse
from botocore.exceptions import ClientError


def fix_resultpath(bucket_name: str, region: str = 'us-east-1'):
    """
    Update Step Functions state machine to use ResultPath correctly
    
    Args:
        bucket_name: S3 bucket name
        region: AWS region
        
    Returns:
        True if successful
    """
    sfn = boto3.client('stepfunctions', region_name=region)
    sts = boto3.client('sts')
    
    account_id = sts.get_caller_identity()['Account']
    state_machine_name = 'MovieLensMLPipeline'
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:{state_machine_name}"
    
    print("\n" + "="*70)
    print("FIXING STATE MACHINE RESULTPATH CONFIGURATION")
    print("="*70 + "\n")
    
    try:
        # Get current state machine definition
        print("[...] Retrieving current state machine definition")
        response = sfn.describe_state_machine(stateMachineArn=state_machine_arn)
        
        definition = json.loads(response['definition'])
        role_arn = response['roleArn']
        
        # Fix DataPreprocessing state
        print("[...] Fixing DataPreprocessing state")
        preprocessing_state = definition['States']['DataPreprocessing']
        preprocessing_state['ResultPath'] = '$.preprocessing_result'
        
        # Fix ModelTraining state
        print("[...] Fixing ModelTraining state")
        training_state = definition['States']['ModelTraining']
        training_state['ResultPath'] = '$.training_result'
        
        # Fix ModelEvaluation state - update Parameters to pass correct model path
        print("[...] Fixing ModelEvaluation state")
        evaluation_state = definition['States']['ModelEvaluation']
        evaluation_state['Parameters'] = {
            "model_data.$": "$.training_result.ModelArtifacts.S3ModelArtifacts",
            "bucket_name": bucket_name,
            "training_job_name.$": "$.training_job_name"
        }
        
        # Update state machine
        print("[...] Updating state machine")
        sfn.update_state_machine(
            stateMachineArn=state_machine_arn,
            definition=json.dumps(definition),
            roleArn=role_arn
        )
        
        print("[OK] Successfully updated state machine")
        print("\nChanges made:")
        print("  1. DataPreprocessing: Added ResultPath to preserve input")
        print("  2. ModelTraining: Added ResultPath to preserve input")
        print("  3. ModelEvaluation: Updated to use training_result path")
        
        print("\n" + "="*70)
        print("HOW RESULTPATH WORKS")
        print("="*70 + "\n")
        
        print("Without ResultPath:")
        print("  Input:  {training_job_name: 'xyz', ...}")
        print("  Output: {ProcessingJobArn: '...'}  <- Original input lost!")
        
        print("\nWith ResultPath:")
        print("  Input:  {training_job_name: 'xyz', ...}")
        print("  Output: {training_job_name: 'xyz', preprocessing_result: {...}}")
        print("          ^ Original input preserved!")
        
        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70 + "\n")
        
        print("The state machine has been updated.")
        print("You can now restart the pipeline:")
        print("  python start_pipeline.py --region us-east-1")
        
        print("\n" + "="*70 + "\n")
        
        return True
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'StateMachineDoesNotExist':
            print(f"[X] State machine not found: {state_machine_name}")
            print("    Run infrastructure deployment first")
            return False
        else:
            print(f"[X] Error updating state machine: {e}")
            return False
    except Exception as e:
        print(f"[X] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Fix ResultPath configuration in Step Functions state machine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix ResultPath configuration
  python fix_state_machine_resultpath.py --bucket amzn-s3-movielens-327030626634
  
  # Fix in different region
  python fix_state_machine_resultpath.py --bucket my-bucket --region us-west-2
        """
    )
    
    parser.add_argument(
        '--bucket',
        required=True,
        help='S3 bucket name'
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    success = fix_resultpath(args.bucket, args.region)
    
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

