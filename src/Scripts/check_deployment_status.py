"""
Quick script to check deployment status
"""
import boto3

def check_status():
    print("\n=== Checking Deployment Status ===\n")
    
    # Check S3 bucket
    s3 = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    try:
        response = s3.list_objects_v2(Bucket=bucket_name, Delimiter='/')
        print(f"[OK] S3 Bucket exists: {bucket_name}")
        if 'CommonPrefixes' in response:
            print("\nDirectories in bucket:")
            for prefix in response['CommonPrefixes']:
                print(f"  - {prefix['Prefix']}")
    except Exception as e:
        print(f"[X] S3 Bucket check failed: {e}")
    
    # Check IAM roles
    iam = boto3.client('iam')
    roles_to_check = [
        'MovieLensSageMakerRole',
        'MovieLensLambdaEvaluationRole',
        'MovieLensLambdaMonitoringRole',
        'MovieLensStepFunctionsRole'
    ]
    
    print("\nIAM Roles:")
    for role_name in roles_to_check:
        try:
            iam.get_role(RoleName=role_name)
            print(f"  [OK] {role_name}")
        except:
            print(f"  [X] {role_name} - Not found")
    
    # Check Lambda functions
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    functions_to_check = [
        'movielens-model-evaluation',
        'movielens-monitoring-setup'
    ]
    
    print("\nLambda Functions:")
    for func_name in functions_to_check:
        try:
            lambda_client.get_function(FunctionName=func_name)
            print(f"  [OK] {func_name}")
        except:
            print(f"  [X] {func_name} - Not found")
    
    # Check Step Functions
    sfn = boto3.client('stepfunctions', region_name='us-east-1')
    try:
        state_machines = sfn.list_state_machines()
        ml_pipeline = [sm for sm in state_machines['stateMachines'] 
                       if 'MovieLens' in sm['name']]
        if ml_pipeline:
            print(f"\nStep Functions:")
            for sm in ml_pipeline:
                print(f"  [OK] {sm['name']}")
        else:
            print(f"\nStep Functions:")
            print(f"  [X] MovieLensMLPipeline - Not found")
    except Exception as e:
        print(f"\nStep Functions:")
        print(f"  [X] Error checking: {e}")
    
    print("\n" + "="*50 + "\n")

if __name__ == '__main__':
    check_status()
