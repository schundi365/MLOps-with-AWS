#!/usr/bin/env python3
"""
Fix Issue #23: Step Functions role missing SageMaker model/endpoint permissions.

Problem: MovieLensStepFunctionsRole doesn't have permissions to:
- sagemaker:CreateModel
- sagemaker:CreateEndpointConfig
- sagemaker:CreateEndpoint

Solution: Add these permissions to the Step Functions role.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #23: Step Functions SageMaker Permissions")
    print("="*70)
    print()
    
    print("Problem: Step Functions role missing model/endpoint permissions")
    print("Solution: Add CreateModel, CreateEndpointConfig, CreateEndpoint")
    print()
    
    iam_client = boto3.client('iam', region_name=region)
    role_name = 'MovieLensStepFunctionsRole'
    
    print(f"Updating role: {role_name}")
    print()
    
    # Policy document with all required SageMaker permissions
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "sagemaker:CreateTrainingJob",
                    "sagemaker:DescribeTrainingJob",
                    "sagemaker:StopTrainingJob",
                    "sagemaker:CreateModel",
                    "sagemaker:CreateEndpointConfig",
                    "sagemaker:CreateEndpoint",
                    "sagemaker:DescribeEndpoint",
                    "sagemaker:DescribeEndpointConfig",
                    "sagemaker:DescribeModel",
                    "sagemaker:DeleteEndpoint",
                    "sagemaker:DeleteEndpointConfig",
                    "sagemaker:DeleteModel",
                    "sagemaker:UpdateEndpoint",
                    "sagemaker:AddTags",
                    "sagemaker:ListTags"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "sagemaker:CreateProcessingJob",
                    "sagemaker:DescribeProcessingJob",
                    "sagemaker:StopProcessingJob"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "lambda:InvokeFunction"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iam:PassRole"
                ],
                "Resource": "arn:aws:iam::327030626634:role/MovieLensSageMakerRole",
                "Condition": {
                    "StringEquals": {
                        "iam:PassedToService": "sagemaker.amazonaws.com"
                    }
                }
            },
            {
                "Effect": "Allow",
                "Action": [
                    "events:PutTargets",
                    "events:PutRule",
                    "events:DescribeRule"
                ],
                "Resource": "*"
            }
        ]
    }
    
    policy_name = 'MovieLensStepFunctionsSageMakerPolicy'
    
    try:
        # Try to update existing policy
        print(f"Checking for existing policy: {policy_name}")
        
        # Get current policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        
        policy_arn = None
        for policy in response['AttachedPolicies']:
            if policy['PolicyName'] == policy_name:
                policy_arn = policy['PolicyArn']
                break
        
        if policy_arn:
            print(f"[OK] Found existing policy: {policy_arn}")
            
            # Get current policy version
            policy_response = iam_client.get_policy(PolicyArn=policy_arn)
            default_version_id = policy_response['Policy']['DefaultVersionId']
            
            # Create new version
            print("Creating new policy version...")
            iam_client.create_policy_version(
                PolicyArn=policy_arn,
                PolicyDocument=json.dumps(policy_document),
                SetAsDefault=True
            )
            
            print("[OK] Policy updated with new permissions")
            
        else:
            print("[!] Policy not found, creating new one...")
            
            # Create new policy
            policy_response = iam_client.create_policy(
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document),
                Description='Permissions for Step Functions to manage SageMaker resources'
            )
            
            policy_arn = policy_response['Policy']['Arn']
            print(f"[OK] Created policy: {policy_arn}")
            
            # Attach to role
            print(f"Attaching policy to role: {role_name}")
            iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            
            print("[OK] Policy attached to role")
        
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print()
    print("="*70)
    print("FIX APPLIED")
    print("="*70)
    print()
    print("Permissions added:")
    print("  - sagemaker:CreateModel")
    print("  - sagemaker:CreateEndpointConfig")
    print("  - sagemaker:CreateEndpoint")
    print("  - sagemaker:DescribeModel")
    print("  - sagemaker:DescribeEndpointConfig")
    print("  - sagemaker:DescribeEndpoint")
    print("  - sagemaker:DeleteModel")
    print("  - sagemaker:DeleteEndpointConfig")
    print("  - sagemaker:DeleteEndpoint")
    print("  - sagemaker:UpdateEndpoint")
    print()
    print("Step Functions can now create models and endpoints!")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
