"""
Fix SageMaker AddTags Permission

This script adds the sagemaker:AddTags permission to the Step Functions role
so it can tag SageMaker training jobs.

Usage:
    python fix_sagemaker_addtags_permission.py
"""
import boto3
import json


def fix_addtags_permission():
    """Add sagemaker:AddTags permission to Step Functions role"""
    
    iam = boto3.client('iam')
    account_id = boto3.client('sts').get_caller_identity()['Account']
    
    print("\n" + "="*70)
    print("FIXING SAGEMAKER ADDTAGS PERMISSION")
    print("="*70 + "\n")
    
    step_functions_role_name = 'MovieLensStepFunctionsRole'
    
    # Policy to allow tagging SageMaker resources
    addtags_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "SageMakerTagging",
                "Effect": "Allow",
                "Action": [
                    "sagemaker:AddTags",
                    "sagemaker:DeleteTags",
                    "sagemaker:ListTags"
                ],
                "Resource": [
                    f"arn:aws:sagemaker:*:{account_id}:training-job/*",
                    f"arn:aws:sagemaker:*:{account_id}:processing-job/*",
                    f"arn:aws:sagemaker:*:{account_id}:model/*",
                    f"arn:aws:sagemaker:*:{account_id}:endpoint/*",
                    f"arn:aws:sagemaker:*:{account_id}:endpoint-config/*"
                ]
            }
        ]
    }
    
    policy_name = "SageMakerTaggingPolicy"
    
    try:
        # Add the policy to the Step Functions role
        print(f"[...] Adding SageMaker tagging policy to {step_functions_role_name}")
        iam.put_role_policy(
            RoleName=step_functions_role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(addtags_policy)
        )
        print(f"[OK] Successfully added SageMaker tagging policy")
        print(f"\nThe Step Functions role can now:")
        print(f"  - Add tags to SageMaker training jobs")
        print(f"  - Add tags to SageMaker processing jobs")
        print(f"  - Add tags to SageMaker models and endpoints")
        return True
        
    except iam.exceptions.NoSuchEntityException:
        print(f"[X] Role {step_functions_role_name} not found")
        print("    Run infrastructure deployment first:")
        print("    python src/infrastructure/deploy_all.py --bucket-name <bucket>")
        return False
        
    except Exception as e:
        print(f"[X] Error adding tagging policy: {e}")
        print("\n[!] You may not have permission to modify IAM roles.")
        print("    Ask your AWS administrator to add this policy to:")
        print(f"    Role: {step_functions_role_name}")
        print(f"\nPolicy Document:")
        print(json.dumps(addtags_policy, indent=2))
        return False


def main():
    success = fix_addtags_permission()
    
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
        print("2. Add inline policy named: SageMakerTaggingPolicy")
        print("3. Policy allows: sagemaker:AddTags, DeleteTags, ListTags")
        print("\nOr run this script with administrator credentials.")
        print("\n" + "="*70 + "\n")


if __name__ == '__main__':
    main()

