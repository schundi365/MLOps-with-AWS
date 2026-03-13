"""
Add Step Functions permissions to your IAM user for monitoring
"""
import boto3
import json

def add_stepfunctions_permissions():
    """Add Step Functions read permissions to the current IAM user"""
    
    iam = boto3.client('iam')
    sts = boto3.client('sts')
    
    # Get current user
    try:
        identity = sts.get_caller_identity()
        user_arn = identity['Arn']
        user_name = user_arn.split('/')[-1]
        print(f"\n[OK] Current user: {user_name}")
        print(f"     ARN: {user_arn}")
    except Exception as e:
        print(f"[X] Error getting user identity: {e}")
        return False
    
    # Define the policy for Step Functions monitoring
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "StepFunctionsMonitoring",
                "Effect": "Allow",
                "Action": [
                    "states:ListStateMachines",
                    "states:ListExecutions",
                    "states:DescribeStateMachine",
                    "states:DescribeExecution",
                    "states:GetExecutionHistory",
                    "states:StartExecution"
                ],
                "Resource": "*"
            },
            {
                "Sid": "CloudWatchLogsRead",
                "Effect": "Allow",
                "Action": [
                    "logs:DescribeLogGroups",
                    "logs:DescribeLogStreams",
                    "logs:GetLogEvents",
                    "logs:FilterLogEvents"
                ],
                "Resource": "*"
            }
        ]
    }
    
    policy_name = "MovieLensStepFunctionsMonitoring"
    
    try:
        # Try to create the policy
        print(f"\n[...] Creating IAM policy: {policy_name}")
        response = iam.create_policy(
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document),
            Description="Allows monitoring of MovieLens Step Functions pipeline"
        )
        policy_arn = response['Policy']['Arn']
        print(f"[OK] Created policy: {policy_arn}")
    except iam.exceptions.EntityAlreadyExistsException:
        # Policy already exists, get its ARN
        account_id = identity['Account']
        policy_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
        print(f"[OK] Policy already exists: {policy_arn}")
    except Exception as e:
        print(f"[X] Error creating policy: {e}")
        print("\n[!] You may not have permission to create IAM policies.")
        print("    Ask your AWS administrator to add these permissions:")
        print("    - states:ListStateMachines")
        print("    - states:ListExecutions")
        print("    - states:DescribeExecution")
        print("    - states:GetExecutionHistory")
        print("    - states:StartExecution")
        return False
    
    # Attach policy to user
    try:
        print(f"\n[...] Attaching policy to user: {user_name}")
        iam.attach_user_policy(
            UserName=user_name,
            PolicyArn=policy_arn
        )
        print(f"[OK] Successfully attached policy to user")
        print(f"\n[OK] Permissions added! You can now monitor the pipeline.")
        return True
    except Exception as e:
        print(f"[X] Error attaching policy: {e}")
        print("\n[!] You may not have permission to attach policies to your user.")
        print("    Ask your AWS administrator to attach this policy:")
        print(f"    Policy ARN: {policy_arn}")
        print(f"    User: {user_name}")
        return False

def main():
    print("\n=== Adding Step Functions Monitoring Permissions ===")
    success = add_stepfunctions_permissions()
    
    if success:
        print("\n" + "="*60)
        print("Next Steps:")
        print("="*60)
        print("\n1. Wait 10-15 seconds for permissions to propagate")
        print("\n2. Try monitoring again:")
        print("   python monitor_pipeline.py")
        print("\n3. Or check status:")
        print("   python check_deployment_status.py")
        print("\n" + "="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("Alternative: Use AWS Console")
        print("="*60)
        print("\nYou can monitor the pipeline in the AWS Console:")
        print("\n1. Go to Step Functions console:")
        print("   https://console.aws.amazon.com/states/home?region=us-east-1")
        print("\n2. Click on 'MovieLensMLPipeline'")
        print("\n3. View executions and their status")
        print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
