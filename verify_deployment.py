"""
Deployment Verification Script

This script checks what infrastructure has been deployed and what steps remain.

Usage:
    python verify_deployment.py --bucket-name movielens-ml-327030626634 --region us-east-1
"""

import boto3
import argparse
from botocore.exceptions import ClientError


def check_s3_bucket(bucket_name: str) -> bool:
    """Check if S3 bucket exists"""
    try:
        s3 = boto3.client('s3')
        s3.head_bucket(Bucket=bucket_name)
        print(f"[OK] S3 Bucket: {bucket_name}")
        
        # Check for data
        response = s3.list_objects_v2(Bucket=bucket_name, Prefix='raw-data/', MaxKeys=1)
        if 'Contents' in response:
            print(f"  [OK] Data uploaded to raw-data/")
        else:
            print(f"  [!] No data in raw-data/ - Need to upload dataset")
        
        return True
    except ClientError as e:
        print(f"[X] S3 Bucket: Not found")
        return False


def check_iam_roles() -> dict:
    """Check if IAM roles exist"""
    iam = boto3.client('iam')
    roles = {
        'SageMaker': 'MovieLensSageMakerRole',
        'Lambda Evaluation': 'MovieLensLambdaEvaluationRole',
        'Lambda Monitoring': 'MovieLensLambdaMonitoringRole',
        'Step Functions': 'MovieLensStepFunctionsRole'
    }
    
    results = {}
    for name, role_name in roles.items():
        try:
            iam.get_role(RoleName=role_name)
            print(f"[OK] IAM Role: {name}")
            results[name] = True
        except ClientError:
            print(f"[X] IAM Role: {name} - Not found")
            results[name] = False
    
    return results


def check_lambda_functions() -> dict:
    """Check if Lambda functions exist"""
    lambda_client = boto3.client('lambda')
    functions = {
        'Evaluation': 'movielens-model-evaluation',
        'Monitoring': 'movielens-monitoring-setup'
    }
    
    results = {}
    for name, func_name in functions.items():
        try:
            lambda_client.get_function(FunctionName=func_name)
            print(f"[OK] Lambda Function: {name}")
            results[name] = True
        except ClientError:
            print(f"[X] Lambda Function: {name} - Not found")
            results[name] = False
    
    return results


def check_step_functions() -> bool:
    """Check if Step Functions state machine exists"""
    sfn = boto3.client('stepfunctions')
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    region = boto3.session.Session().region_name or 'us-east-1'
    
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:MovieLensMLPipeline"
    
    try:
        response = sfn.describe_state_machine(stateMachineArn=state_machine_arn)
        print(f"[OK] Step Functions: MovieLensMLPipeline")
        
        # Check execution history
        executions = sfn.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=1
        )
        
        if executions['executions']:
            latest = executions['executions'][0]
            print(f"  [OK] Latest execution: {latest['status']}")
            print(f"      Started: {latest['startDate']}")
        else:
            print(f"  [!] No executions yet - Need to start pipeline")
        
        return True
    except ClientError:
        print(f"[X] Step Functions: MovieLensMLPipeline - Not found")
        return False


def check_eventbridge() -> bool:
    """Check if EventBridge rule exists"""
    events = boto3.client('events')
    
    try:
        response = events.describe_rule(Name='MovieLensWeeklyRetraining')
        print(f"[OK] EventBridge Rule: MovieLensWeeklyRetraining")
        print(f"  Schedule: {response.get('ScheduleExpression', 'N/A')}")
        print(f"  State: {response.get('State', 'N/A')}")
        return True
    except ClientError:
        print(f"[!] EventBridge Rule: Not found (deployed with --skip-eventbridge)")
        return False


def check_sagemaker_resources() -> dict:
    """Check if SageMaker resources exist"""
    sagemaker = boto3.client('sagemaker')
    
    results = {}
    
    # Check for training jobs
    try:
        training_jobs = sagemaker.list_training_jobs(
            MaxResults=1,
            SortBy='CreationTime',
            SortOrder='Descending'
        )
        
        if training_jobs['TrainingJobSummaries']:
            latest = training_jobs['TrainingJobSummaries'][0]
            print(f"[OK] Training Job: {latest['TrainingJobName']}")
            print(f"  Status: {latest['TrainingJobStatus']}")
            print(f"  Created: {latest['CreationTime']}")
            results['training'] = True
        else:
            print(f"[!] Training Job: None found - Need to start pipeline")
            results['training'] = False
    except ClientError as e:
        print(f"[X] Training Job: Error checking - {e}")
        results['training'] = False
    
    # Check for endpoints
    try:
        endpoints = sagemaker.list_endpoints(
            MaxResults=1,
            SortBy='CreationTime',
            SortOrder='Descending'
        )
        
        if endpoints['Endpoints']:
            latest = endpoints['Endpoints'][0]
            print(f"[OK] Endpoint: {latest['EndpointName']}")
            print(f"  Status: {latest['EndpointStatus']}")
            print(f"  Created: {latest['CreationTime']}")
            results['endpoint'] = True
        else:
            print(f"[!] Endpoint: None found - Need to complete training")
            results['endpoint'] = False
    except ClientError as e:
        print(f"[X] Endpoint: Error checking - {e}")
        results['endpoint'] = False
    
    return results


def print_next_steps(checks: dict):
    """Print next steps based on what's deployed"""
    print("\n" + "="*70)
    print("DEPLOYMENT STATUS SUMMARY")
    print("="*70 + "\n")
    
    infrastructure_ready = all([
        checks.get('s3', False),
        checks.get('iam', {}).get('SageMaker', False),
        checks.get('lambda', {}).get('Evaluation', False),
        checks.get('step_functions', False)
    ])
    
    if not infrastructure_ready:
        print("[!] INFRASTRUCTURE NOT COMPLETE")
        print("\nNext Step: Deploy infrastructure")
        print("  python src\\infrastructure\\deploy_all.py --bucket-name <bucket> --region us-east-1")
        return
    
    print("[OK] INFRASTRUCTURE DEPLOYED")
    
    if not checks.get('data_uploaded', False):
        print("\n[!] DATA NOT UPLOADED")
        print("\nNext Step: Upload MovieLens dataset")
        print("  python src\\data_upload.py --dataset 100k --bucket <bucket> --prefix raw-data/")
        return
    
    print("[OK] DATA UPLOADED")
    
    if not checks.get('sagemaker', {}).get('training', False):
        print("\n[!] MODEL NOT TRAINED")
        print("\nNext Step: Start ML pipeline")
        print("  1. Go to AWS Console -> Step Functions")
        print("  2. Click 'MovieLensMLPipeline'")
        print("  3. Click 'Start execution'")
        print("  4. Click 'Start execution' again (no input needed)")
        print("\n  Or use CLI:")
        print("  aws stepfunctions start-execution --state-machine-arn <arn>")
        return
    
    print("[OK] MODEL TRAINED")
    
    if not checks.get('sagemaker', {}).get('endpoint', False):
        print("\n[!] ENDPOINT NOT DEPLOYED")
        print("\nNext Step: Wait for pipeline to complete")
        print("  Training takes 30-45 minutes")
        print("  Check status in Step Functions console")
        return
    
    print("[OK] ENDPOINT DEPLOYED")
    print("\n[OK] SYSTEM FULLY OPERATIONAL!")
    print("\nYou can now:")
    print("  1. View metrics in CloudWatch Dashboard")
    print("  2. Monitor endpoint in SageMaker console")
    print("  3. Make predictions via endpoint")
    print("  4. Check Model Monitor for data drift")


def main():
    """Main verification function"""
    parser = argparse.ArgumentParser(description='Verify MovieLens deployment status')
    parser.add_argument('--bucket-name', required=True, help='S3 bucket name')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    # Set region
    boto3.setup_default_session(region_name=args.region)
    
    print("\n" + "="*70)
    print("MOVIELENS DEPLOYMENT VERIFICATION")
    print("="*70 + "\n")
    
    checks = {}
    
    print("Checking Infrastructure Components...\n")
    
    # Check S3
    checks['s3'] = check_s3_bucket(args.bucket_name)
    checks['data_uploaded'] = checks['s3']  # Will be updated by check_s3_bucket
    
    print()
    
    # Check IAM
    checks['iam'] = check_iam_roles()
    print()
    
    # Check Lambda
    checks['lambda'] = check_lambda_functions()
    print()
    
    # Check Step Functions
    checks['step_functions'] = check_step_functions()
    print()
    
    # Check EventBridge
    checks['eventbridge'] = check_eventbridge()
    print()
    
    # Check SageMaker
    print("Checking ML Pipeline Components...\n")
    checks['sagemaker'] = check_sagemaker_resources()
    
    # Print next steps
    print_next_steps(checks)
    
    print("\n" + "="*70)


if __name__ == '__main__':
    main()
