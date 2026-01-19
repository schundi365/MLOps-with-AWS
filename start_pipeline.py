"""
Start ML Pipeline Script

This script starts the MovieLens ML pipeline execution.

Usage:
    python start_pipeline.py --region us-east-1
"""

import boto3
import argparse
import json
from botocore.exceptions import ClientError


def start_pipeline(region: str = 'us-east-1') -> bool:
    """
    Start the ML pipeline execution
    
    Args:
        region: AWS region
        
    Returns:
        True if started successfully
    """
    sfn = boto3.client('stepfunctions', region_name=region)
    sts = boto3.client('sts')
    
    # Get account ID
    account_id = sts.get_caller_identity()['Account']
    
    # Construct state machine ARN
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:MovieLensMLPipeline"
    
    try:
        # Generate unique execution name and job names
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        execution_name = f"execution-{timestamp}"
        
        # Prepare input with required parameters
        pipeline_input = {
            "preprocessing_job_name": f"movielens-preprocessing-{timestamp}",
            "training_job_name": f"movielens-training-{timestamp}",
            "endpoint_name": f"movielens-endpoint-{timestamp}",
            "endpoint_config_name": f"movielens-endpoint-config-{timestamp}"
        }
        
        # Start execution
        response = sfn.start_execution(
            stateMachineArn=state_machine_arn,
            name=execution_name,
            input=json.dumps(pipeline_input)
        )
        
        execution_arn = response['executionArn']
        
        print("\n" + "="*70)
        print("ML PIPELINE STARTED SUCCESSFULLY!")
        print("="*70 + "\n")
        
        print(f"Execution ARN: {execution_arn}")
        print(f"Start Time: {response['startDate']}")
        
        print("\n" + "="*70)
        print("WHAT HAPPENS NEXT")
        print("="*70 + "\n")
        
        print("The pipeline will execute these steps:")
        print("  1. Data Preprocessing      (~5-10 minutes)")
        print("  2. Model Training          (~30-45 minutes)")
        print("  3. Model Evaluation        (~2-5 minutes)")
        print("  4. Model Deployment        (~5-10 minutes)")
        print("  5. Monitoring Setup        (~1-2 minutes)")
        print("\n  Total Time: ~45-75 minutes")
        
        print("\n" + "="*70)
        print("HOW TO MONITOR PROGRESS")
        print("="*70 + "\n")
        
        print("Option 1: AWS Console (Recommended)")
        print(f"  1. Go to: https://console.aws.amazon.com/states/home?region={region}#/statemachines")
        print("  2. Click 'MovieLensMLPipeline'")
        print("  3. Click on the running execution")
        print("  4. Watch the visual workflow progress")
        
        print("\nOption 2: CLI")
        print(f"  aws stepfunctions describe-execution --execution-arn {execution_arn}")
        
        print("\nOption 3: Python Script")
        print(f"  python monitor_pipeline.py --execution-arn {execution_arn}")
        
        print("\n" + "="*70)
        print("AFTER COMPLETION")
        print("="*70 + "\n")
        
        print("Once the pipeline completes successfully:")
        print("  - Model will be deployed to SageMaker endpoint")
        print("  - CloudWatch dashboard will show metrics")
        print("  - Model Monitor will start tracking drift")
        print("  - You can make predictions via the endpoint")
        
        print("\nVerify completion:")
        print("  python verify_deployment.py --bucket-name <bucket> --region us-east-1")
        
        print("\n" + "="*70)
        
        return True
        
    except ClientError as e:
        print(f"\n[X] Error starting pipeline: {e}")
        print(f"    Error Code: {e.response['Error']['Code']}")
        print(f"    Error Message: {e.response['Error']['Message']}")
        
        if e.response['Error']['Code'] == 'StateMachineDoesNotExist':
            print("\n[!] State machine not found. Did you deploy infrastructure?")
            print("    Run: python src\\infrastructure\\deploy_all.py --bucket-name <bucket> --region us-east-1")
        
        return False
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        return False


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description='Start MovieLens ML pipeline execution',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start pipeline in us-east-1
  python start_pipeline.py --region us-east-1
  
  # Start pipeline in different region
  python start_pipeline.py --region us-west-2
        """
    )
    
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("STARTING MOVIELENS ML PIPELINE")
    print("="*70 + "\n")
    
    print("This will:")
    print("  - Start the Step Functions state machine")
    print("  - Preprocess the MovieLens data")
    print("  - Train the collaborative filtering model")
    print("  - Evaluate model performance")
    print("  - Deploy model to SageMaker endpoint")
    print("  - Setup monitoring and drift detection")
    
    print("\nEstimated time: 45-75 minutes")
    print("Estimated cost: ~$5-10 for this training run")
    
    response = input("\nProceed? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("\n[!] Pipeline start cancelled")
        return 1
    
    success = start_pipeline(args.region)
    
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
