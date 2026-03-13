"""
Fix iam:PassRole permission for Step Functions execution

This script adds the iam:PassRole permission to the Step Functions role
so it can pass the SageMaker role to SageMaker services.
"""
import boto3
import json

def fix_passrole_permission():
    """Add iam:PassRole permission to Step Functions role"""
    
    iam = boto3.client('iam')
    account_id = boto3.client('sts').get_caller_identity()['Account']
    
    print("\n=== Fixing iam:PassRole Permission ===\n")
    
    # The Step Functions role needs to pass the SageMaker role
    step_functions_role_name = 'MovieLensStepFunctionsRole'
    sagemaker_role_arn = f"arn:aws:iam::{account_id}:role/MovieLensSageMakerRole"
    
    # Policy to allow passing the SageMaker role
    pass_role_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PassRoleToSageMaker",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": [
                    sagemaker_role_arn,
                    f"arn:aws:iam::{account_id}:role/MovieLensLambdaEvaluationRole",
                    f"arn:aws:iam::{account_id}:role/MovieLensLambdaMonitoringRole"
                ],
                "Condition": {
                    "StringEquals": {
                        "iam:PassedToService": [
                            "sagemaker.amazonaws.com",
                            "lambda.amazonaws.com"
                        ]
                    }
                }
            }
        ]
    }
    
    policy_name = "PassRolePolicy"
    
    try:
        # Add the policy to the Step Functions role
        print(f"[...] Adding PassRole policy to {step_functions_role_name}")
        iam.put_role_policy(
            RoleName=step_functions_role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(pass_role_policy)
        )
        print(f"[OK] Successfully added PassRole policy")
        print(f"\nThe Step Functions role can now pass:")
        print(f"  - MovieLensSageMakerRole to SageMaker")
        print(f"  - Lambda roles to Lambda functions")
        return True
        
    except iam.exceptions.NoSuchEntityException:
        print(f"[X] Role {step_functions_role_name} not found")
        print("    Run infrastructure deployment first:")
        print("    python src/infrastructure/deploy_all.py --bucket-name <bucket>")
        return False
        
    except Exception as e:
        print(f"[X] Error adding PassRole policy: {e}")
        print("\n[!] You may not have permission to modify IAM roles.")
        print("    Ask your AWS administrator to add this policy to:")
        print(f"    Role: {step_functions_role_name}")
        print(f"\nPolicy Document:")
        print(json.dumps(pass_role_policy, indent=2))
        return False

def main():
    success = fix_passrole_permission()
    
    if success:
        print("\n" + "="*70)
        print("Permission Fixed!")
        print("="*70)
        print("\nYou can now restart the pipeline:")
        print("  python start_pipeline.py --region us-east-1")
        print("\n" + "="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("Manual Fix Required")
        print("="*70)
        print("\nSend this information to your AWS administrator:")
        print("\n1. Role to modify: MovieLensStepFunctionsRole")
        print("2. Add inline policy named: PassRolePolicy")
        print("3. Policy allows: iam:PassRole for SageMaker and Lambda roles")
        print("\nOr run this script with administrator credentials.")
        print("\n" + "="*70 + "\n")

if __name__ == '__main__':
    main()
