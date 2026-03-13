"""
Fix Preprocessing Input in Step Functions

This script updates the Step Functions state machine to include the
preprocessing.py script as an input to the processing job.

Usage:
    python fix_preprocessing_input.py --bucket amzn-s3-movielens-327030626634
"""

import boto3
import json
import argparse
from botocore.exceptions import ClientError


def fix_preprocessing_input(bucket_name: str, region: str = 'us-east-1'):
    """
    Update Step Functions state machine to include preprocessing code
    
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
    print("FIXING PREPROCESSING INPUT IN STEP FUNCTIONS")
    print("="*70 + "\n")
    
    try:
        # Get current state machine definition
        print("[...] Retrieving current state machine definition")
        response = sfn.describe_state_machine(stateMachineArn=state_machine_arn)
        
        definition = json.loads(response['definition'])
        role_arn = response['roleArn']
        
        # Update DataPreprocessing state to include code input
        print("[...] Updating DataPreprocessing state")
        
        preprocessing_state = definition['States']['DataPreprocessing']
        
        # Add code input to ProcessingInputs
        preprocessing_state['Parameters']['ProcessingInputs'] = [
            {
                "InputName": "code",
                "S3Input": {
                    "S3Uri": f"s3://{bucket_name}/code/preprocessing.py",
                    "LocalPath": "/opt/ml/processing/input/code",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File"
                }
            },
            {
                "InputName": "raw-data",
                "S3Input": {
                    "S3Uri": f"s3://{bucket_name}/raw-data/",
                    "LocalPath": "/opt/ml/processing/input/data",
                    "S3DataType": "S3Prefix",
                    "S3InputMode": "File"
                }
            }
        ]
        
        # Update container entrypoint to use correct path
        preprocessing_state['Parameters']['AppSpecification']['ContainerEntrypoint'] = [
            "python3",
            "/opt/ml/processing/input/code/preprocessing.py"
        ]
        
        # Update state machine
        print("[...] Updating state machine")
        sfn.update_state_machine(
            stateMachineArn=state_machine_arn,
            definition=json.dumps(definition),
            roleArn=role_arn
        )
        
        print("[OK] Successfully updated state machine")
        print("\nChanges made:")
        print("  1. Added preprocessing code as input")
        print("  2. Updated code path: /opt/ml/processing/input/code/preprocessing.py")
        print("  3. Updated data path: /opt/ml/processing/input/data/")
        
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
        description='Fix preprocessing input in Step Functions state machine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix preprocessing input
  python fix_preprocessing_input.py --bucket amzn-s3-movielens-327030626634
  
  # Fix in different region
  python fix_preprocessing_input.py --bucket my-bucket --region us-west-2
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
    
    success = fix_preprocessing_input(args.bucket, args.region)
    
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())

