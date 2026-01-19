"""
Complete the deployment by deploying Step Functions and EventBridge
"""
import sys
import os

# Add src/infrastructure to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'infrastructure'))

from stepfunctions_deployment import StepFunctionsDeployment
from eventbridge_deployment import EventBridgeDeployment
import boto3

def main():
    print("\n=== Completing Infrastructure Deployment ===\n")
    
    region = 'us-east-1'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    # Get role ARNs
    iam = boto3.client('iam')
    
    try:
        sagemaker_role = iam.get_role(RoleName='MovieLensSageMakerRole')
        sagemaker_role_arn = sagemaker_role['Role']['Arn']
        
        sfn_role = iam.get_role(RoleName='MovieLensStepFunctionsRole')
        sfn_role_arn = sfn_role['Role']['Arn']
        
        print(f"[OK] Retrieved IAM role ARNs")
    except Exception as e:
        print(f"[X] Error getting IAM roles: {e}")
        return False
    
    # Get Lambda ARNs
    lambda_client = boto3.client('lambda', region_name=region)
    
    try:
        eval_func = lambda_client.get_function(FunctionName='movielens-model-evaluation')
        evaluation_lambda_arn = eval_func['Configuration']['FunctionArn']
        
        monitor_func = lambda_client.get_function(FunctionName='movielens-monitoring-setup')
        monitoring_lambda_arn = monitor_func['Configuration']['FunctionArn']
        
        print(f"[OK] Retrieved Lambda function ARNs")
    except Exception as e:
        print(f"[X] Error getting Lambda functions: {e}")
        return False
    
    # Deploy Step Functions
    print("\n[1/2] Deploying Step Functions state machine...")
    sfn_deployment = StepFunctionsDeployment(region)
    state_machine_arn = sfn_deployment.deploy_ml_pipeline(
        state_machine_name='MovieLensMLPipeline',
        role_arn=sfn_role_arn,
        bucket_name=bucket_name,
        sagemaker_role_arn=sagemaker_role_arn,
        evaluation_lambda_arn=evaluation_lambda_arn,
        monitoring_lambda_arn=monitoring_lambda_arn
    )
    
    if not state_machine_arn:
        print("[X] Failed to deploy Step Functions")
        return False
    
    # Deploy EventBridge (optional)
    print("\n[2/2] Deploying EventBridge scheduled retraining...")
    eventbridge_deployment = EventBridgeDeployment(region)
    eventbridge_success = eventbridge_deployment.deploy_complete_schedule(
        rule_name='MovieLensWeeklyRetraining',
        state_machine_arn=state_machine_arn
    )
    
    if not eventbridge_success:
        print("\n[!] Warning: EventBridge deployment failed")
        print("    You can manually trigger the pipeline via Step Functions console")
    
    # Final summary
    print("\n" + "="*70)
    print("Infrastructure Deployment Complete!")
    print("="*70)
    print(f"\n[OK] S3 Bucket: {bucket_name}")
    print(f"[OK] SageMaker Role: {sagemaker_role_arn}")
    print(f"[OK] Lambda Evaluation: {evaluation_lambda_arn}")
    print(f"[OK] Lambda Monitoring: {monitoring_lambda_arn}")
    print(f"[OK] Step Functions: {state_machine_arn}")
    if eventbridge_success:
        print(f"[OK] EventBridge Rule: MovieLensWeeklyRetraining")
    else:
        print(f"[!] EventBridge Rule: Failed (manual trigger required)")
    
    print("\n" + "="*70)
    print("Next Steps:")
    print("="*70)
    print("\n1. Upload MovieLens dataset:")
    print(f"   python src/data_upload.py --dataset 100k --bucket {bucket_name} --prefix raw-data/")
    print("\n2. Start the ML pipeline:")
    print("   python start_pipeline.py")
    print("\n3. Monitor pipeline execution:")
    print("   python monitor_pipeline.py")
    print("\n" + "="*70 + "\n")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
