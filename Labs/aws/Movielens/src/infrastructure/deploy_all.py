"""
Master Deployment Script for MovieLens Recommendation System

This script orchestrates the complete infrastructure deployment:
1. S3 bucket setup
2. IAM roles and policies
3. Lambda functions
4. Step Functions state machine
5. EventBridge scheduled retraining

Usage:
    python deploy_all.py --bucket-name movielens-ml-bucket --region us-east-1
"""

import argparse
import sys
from s3_setup import S3BucketSetup
from iam_setup import IAMSetup
from lambda_deployment import LambdaDeployment
from stepfunctions_deployment import StepFunctionsDeployment
from eventbridge_deployment import EventBridgeDeployment


def deploy_infrastructure(
    bucket_name: str,
    region: str = 'us-east-1',
    kms_key_id: str = None
):
    """
    Deploy complete infrastructure for MovieLens recommendation system
    
    Args:
        bucket_name: Name for the S3 bucket
        region: AWS region
        kms_key_id: Optional KMS key ID for encryption
    """
    print("\n" + "="*70)
    print("MovieLens Recommendation System - Infrastructure Deployment")
    print("="*70 + "\n")
    
    # Step 1: Setup IAM roles
    print("\n[1/5] Setting up IAM roles...")
    iam_setup = IAMSetup()
    roles = iam_setup.setup_all_roles(bucket_name=bucket_name)
    
    if len(roles) != 4:
        print("\n✗ Failed to create all required IAM roles")
        return False
    
    sagemaker_role_arn = roles['sagemaker']
    lambda_eval_role_arn = roles['lambda_evaluation']
    lambda_monitor_role_arn = roles['lambda_monitoring']
    step_functions_role_arn = roles['step_functions']
    
    # Step 2: Setup S3 bucket
    print("\n[2/5] Setting up S3 bucket...")
    s3_setup = S3BucketSetup(bucket_name, region)
    s3_success = s3_setup.setup_complete_bucket(
        sagemaker_role_arn=sagemaker_role_arn,
        lambda_role_arns=[lambda_eval_role_arn, lambda_monitor_role_arn],
        kms_key_id=kms_key_id
    )
    
    if not s3_success:
        print("\n✗ Failed to setup S3 bucket")
        return False
    
    # Step 3: Deploy Lambda functions
    print("\n[3/5] Deploying Lambda functions...")
    lambda_deployment = LambdaDeployment(region)
    lambda_functions = lambda_deployment.deploy_all_lambda_functions(
        bucket_name=bucket_name,
        evaluation_role_arn=lambda_eval_role_arn,
        monitoring_role_arn=lambda_monitor_role_arn
    )
    
    if len(lambda_functions) != 2:
        print("\n✗ Failed to deploy all Lambda functions")
        return False
    
    evaluation_lambda_arn = lambda_functions['evaluation']
    monitoring_lambda_arn = lambda_functions['monitoring']
    
    # Step 4: Deploy Step Functions state machine
    print("\n[4/5] Deploying Step Functions state machine...")
    sfn_deployment = StepFunctionsDeployment(region)
    state_machine_arn = sfn_deployment.deploy_ml_pipeline(
        state_machine_name='MovieLensMLPipeline',
        role_arn=step_functions_role_arn,
        bucket_name=bucket_name,
        sagemaker_role_arn=sagemaker_role_arn,
        evaluation_lambda_arn=evaluation_lambda_arn,
        monitoring_lambda_arn=monitoring_lambda_arn
    )
    
    if not state_machine_arn:
        print("\n✗ Failed to deploy Step Functions state machine")
        return False
    
    # Step 5: Deploy EventBridge scheduled retraining
    print("\n[5/5] Deploying EventBridge scheduled retraining...")
    eventbridge_deployment = EventBridgeDeployment(region)
    eventbridge_success = eventbridge_deployment.deploy_complete_schedule(
        rule_name='MovieLensWeeklyRetraining',
        state_machine_arn=state_machine_arn
    )
    
    if not eventbridge_success:
        print("\n✗ Failed to deploy EventBridge schedule")
        return False
    
    # Deployment summary
    print("\n" + "="*70)
    print("Deployment Summary")
    print("="*70)
    print(f"\n✓ S3 Bucket: {bucket_name}")
    print(f"✓ SageMaker Role: {sagemaker_role_arn}")
    print(f"✓ Lambda Evaluation: {evaluation_lambda_arn}")
    print(f"✓ Lambda Monitoring: {monitoring_lambda_arn}")
    print(f"✓ Step Functions: {state_machine_arn}")
    print(f"✓ EventBridge Rule: MovieLensWeeklyRetraining")
    
    print("\n" + "="*70)
    print("Infrastructure Deployment Complete!")
    print("="*70 + "\n")
    
    print("Next steps:")
    print("1. Upload MovieLens dataset to S3: s3://{}/raw-data/".format(bucket_name))
    print("2. Upload preprocessing script to S3")
    print("3. Start the ML pipeline via Step Functions console or CLI")
    print("4. Monitor pipeline execution in Step Functions console")
    
    return True


def main():
    """Main function for standalone execution"""
    parser = argparse.ArgumentParser(
        description='Deploy complete infrastructure for MovieLens recommendation system',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy with default settings
  python deploy_all.py --bucket-name movielens-ml-bucket
  
  # Deploy with custom region and KMS encryption
  python deploy_all.py --bucket-name movielens-ml-bucket --region us-west-2 --kms-key-id <key-id>
        """
    )
    
    parser.add_argument(
        '--bucket-name',
        required=True,
        help='Name for the S3 bucket (must be globally unique)'
    )
    parser.add_argument(
        '--region',
        default='us-east-1',
        help='AWS region (default: us-east-1)'
    )
    parser.add_argument(
        '--kms-key-id',
        help='Optional KMS key ID for S3 encryption'
    )
    
    args = parser.parse_args()
    
    # Validate bucket name
    if not args.bucket_name or len(args.bucket_name) < 3:
        print("✗ Error: Bucket name must be at least 3 characters")
        sys.exit(1)
    
    # Deploy infrastructure
    success = deploy_infrastructure(
        bucket_name=args.bucket_name,
        region=args.region,
        kms_key_id=args.kms_key_id
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
