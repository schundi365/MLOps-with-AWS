"""
Add EventBridge Permissions to IAM User

This script adds the necessary EventBridge permissions to your IAM user
so that the deployment can create scheduled retraining rules.

Usage:
    python add_eventbridge_permissions.py --user-name dev
"""

import boto3
import json
import argparse
from botocore.exceptions import ClientError


def add_eventbridge_permissions(user_name: str) -> bool:
    """
    Add EventBridge permissions to an IAM user
    
    Args:
        user_name: Name of the IAM user
        
    Returns:
        True if successful, False otherwise
    """
    iam_client = boto3.client('iam')
    
    # EventBridge policy
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "events:PutRule",
                    "events:PutTargets",
                    "events:DescribeRule",
                    "events:DeleteRule",
                    "events:RemoveTargets",
                    "events:ListRules",
                    "events:ListTargetsByRule"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "iam:PassRole"
                ],
                "Resource": "*",
                "Condition": {
                    "StringEquals": {
                        "iam:PassedToService": "events.amazonaws.com"
                    }
                }
            }
        ]
    }
    
    policy_name = "EventBridgeDeploymentAccess"
    
    try:
        # Check if policy already exists
        try:
            iam_client.get_user_policy(
                UserName=user_name,
                PolicyName=policy_name
            )
            print(f"[!] Policy '{policy_name}' already exists for user '{user_name}'")
            
            # Update the policy
            iam_client.put_user_policy(
                UserName=user_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            print(f"[OK] Updated policy '{policy_name}' for user '{user_name}'")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                # Policy doesn't exist, create it
                iam_client.put_user_policy(
                    UserName=user_name,
                    PolicyName=policy_name,
                    PolicyDocument=json.dumps(policy_document)
                )
                print(f"[OK] Created policy '{policy_name}' for user '{user_name}'")
            else:
                raise
        
        print("\n" + "="*70)
        print("EventBridge Permissions Added Successfully!")
        print("="*70)
        print(f"\nUser '{user_name}' can now:")
        print("  - Create EventBridge rules")
        print("  - Add targets to rules")
        print("  - Manage scheduled events")
        print("\nYou can now run the full deployment without --skip-eventbridge:")
        print("  python src\\infrastructure\\deploy_all.py --bucket-name <bucket> --region us-east-1")
        
        return True
        
    except ClientError as e:
        print(f"[X] Error adding permissions: {e}")
        print(f"    Error Code: {e.response['Error']['Code']}")
        print(f"    Error Message: {e.response['Error']['Message']}")
        
        if e.response['Error']['Code'] == 'AccessDenied':
            print("\n[!] You don't have permission to modify IAM policies.")
            print("    Ask your AWS administrator to add EventBridge permissions.")
            print("    Or use --skip-eventbridge flag to deploy without automated scheduling.")
        
        return False
    except Exception as e:
        print(f"[X] Unexpected error: {e}")
        return False


def main():
    """Main function for standalone execution"""
    parser = argparse.ArgumentParser(
        description='Add EventBridge permissions to IAM user',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add permissions to user 'dev'
  python add_eventbridge_permissions.py --user-name dev
  
  # Add permissions to current user (auto-detect)
  python add_eventbridge_permissions.py --auto
        """
    )
    
    parser.add_argument(
        '--user-name',
        help='Name of the IAM user to add permissions to'
    )
    parser.add_argument(
        '--auto',
        action='store_true',
        help='Auto-detect current user from AWS credentials'
    )
    
    args = parser.parse_args()
    
    # Determine user name
    if args.auto:
        try:
            sts_client = boto3.client('sts')
            identity = sts_client.get_caller_identity()
            arn = identity['Arn']
            # Extract user name from ARN: arn:aws:iam::123456789012:user/username
            user_name = arn.split('/')[-1]
            print(f"[OK] Auto-detected user: {user_name}")
        except Exception as e:
            print(f"[X] Failed to auto-detect user: {e}")
            print("    Please specify --user-name manually")
            return 1
    elif args.user_name:
        user_name = args.user_name
    else:
        print("[X] Error: Must specify either --user-name or --auto")
        parser.print_help()
        return 1
    
    # Add permissions
    success = add_eventbridge_permissions(user_name)
    
    return 0 if success else 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
