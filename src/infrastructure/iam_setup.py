"""
IAM Roles and Policies Setup Script for MovieLens Recommendation System

This script creates IAM roles with least-privilege policies for:
- SageMaker execution role
- Lambda execution roles (evaluation and monitoring)
- Step Functions execution role

Requirements: 12.1
"""

import boto3
import json
from typing import Dict, Optional
from botocore.exceptions import ClientError


class IAMSetup:
    """Manages IAM role and policy creation for the ML pipeline"""
    
    def __init__(self):
        """Initialize IAM setup"""
        self.iam_client = boto3.client('iam')
        
    def create_role(self, role_name: str, assume_role_policy: Dict) -> Optional[str]:
        """
        Create IAM role with trust policy
        
        Args:
            role_name: Name of the IAM role
            assume_role_policy: Trust policy document
            
        Returns:
            Role ARN if successful, None otherwise
        """
        try:
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                Description=f'Execution role for {role_name}'
            )
            role_arn = response['Role']['Arn']
            print(f"✓ Created role: {role_name}")
            return role_arn
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                # Get existing role ARN
                response = self.iam_client.get_role(RoleName=role_name)
                role_arn = response['Role']['Arn']
                print(f"✓ Role already exists: {role_name}")
                return role_arn
            else:
                print(f"✗ Error creating role {role_name}: {e}")
                return None
    
    def attach_policy(self, role_name: str, policy_arn: str) -> bool:
        """
        Attach managed policy to role
        
        Args:
            role_name: Name of the IAM role
            policy_arn: ARN of the policy to attach
            
        Returns:
            True if successful
        """
        try:
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn=policy_arn
            )
            return True
        except ClientError as e:
            print(f"✗ Error attaching policy to {role_name}: {e}")
            return False
    
    def create_inline_policy(self, role_name: str, policy_name: str, policy_document: Dict) -> bool:
        """
        Create inline policy for role
        
        Args:
            role_name: Name of the IAM role
            policy_name: Name of the inline policy
            policy_document: Policy document
            
        Returns:
            True if successful
        """
        try:
            self.iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName=policy_name,
                PolicyDocument=json.dumps(policy_document)
            )
            print(f"✓ Created inline policy: {policy_name} for {role_name}")
            return True
        except ClientError as e:
            print(f"✗ Error creating inline policy for {role_name}: {e}")
            return False
    
    def create_sagemaker_execution_role(
        self,
        role_name: str,
        bucket_name: str
    ) -> Optional[str]:
        """
        Create SageMaker execution role with least-privilege policies
        
        Args:
            role_name: Name for the SageMaker role
            bucket_name: S3 bucket name for data access
            
        Returns:
            Role ARN if successful
        """
        print(f"\n--- Creating SageMaker Execution Role ---")
        
        # Trust policy for SageMaker
        assume_role_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Principal': {'Service': 'sagemaker.amazonaws.com'},
                'Action': 'sts:AssumeRole'
            }]
        }
        
        role_arn = self.create_role(role_name, assume_role_policy)
        if not role_arn:
            return None
        
        # Attach AWS managed policy for SageMaker
        self.attach_policy(role_name, 'arn:aws:iam::aws:policy/AmazonSageMakerFullAccess')
        
        # Create custom inline policy for S3 access
        s3_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        's3:GetObject',
                        's3:PutObject',
                        's3:DeleteObject',
                        's3:ListBucket'
                    ],
                    'Resource': [
                        f'arn:aws:s3:::{bucket_name}',
                        f'arn:aws:s3:::{bucket_name}/*'
                    ]
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'cloudwatch:PutMetricData',
                        'logs:CreateLogGroup',
                        'logs:CreateLogStream',
                        'logs:PutLogEvents'
                    ],
                    'Resource': '*'
                }
            ]
        }
        
        self.create_inline_policy(role_name, 'SageMakerS3Access', s3_policy)
        
        return role_arn
    
    def create_lambda_evaluation_role(
        self,
        role_name: str,
        bucket_name: str,
        sagemaker_endpoint_name: str = '*'
    ) -> Optional[str]:
        """
        Create Lambda execution role for model evaluation
        
        Args:
            role_name: Name for the Lambda role
            bucket_name: S3 bucket name for data access
            sagemaker_endpoint_name: SageMaker endpoint name pattern
            
        Returns:
            Role ARN if successful
        """
        print(f"\n--- Creating Lambda Evaluation Role ---")
        
        # Trust policy for Lambda
        assume_role_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Principal': {'Service': 'lambda.amazonaws.com'},
                'Action': 'sts:AssumeRole'
            }]
        }
        
        role_arn = self.create_role(role_name, assume_role_policy)
        if not role_arn:
            return None
        
        # Attach AWS managed policy for Lambda basic execution
        self.attach_policy(role_name, 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')
        
        # Create custom inline policy for S3 and SageMaker access
        lambda_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        's3:GetObject',
                        's3:PutObject'
                    ],
                    'Resource': [
                        f'arn:aws:s3:::{bucket_name}/processed-data/*',
                        f'arn:aws:s3:::{bucket_name}/metrics/*'
                    ]
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'sagemaker:InvokeEndpoint'
                    ],
                    'Resource': f'arn:aws:sagemaker:*:*:endpoint/{sagemaker_endpoint_name}'
                }
            ]
        }
        
        self.create_inline_policy(role_name, 'LambdaEvaluationAccess', lambda_policy)
        
        return role_arn
    
    def create_lambda_monitoring_role(
        self,
        role_name: str,
        bucket_name: str
    ) -> Optional[str]:
        """
        Create Lambda execution role for monitoring setup
        
        Args:
            role_name: Name for the Lambda role
            bucket_name: S3 bucket name for monitoring data
            
        Returns:
            Role ARN if successful
        """
        print(f"\n--- Creating Lambda Monitoring Role ---")
        
        # Trust policy for Lambda
        assume_role_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Principal': {'Service': 'lambda.amazonaws.com'},
                'Action': 'sts:AssumeRole'
            }]
        }
        
        role_arn = self.create_role(role_name, assume_role_policy)
        if not role_arn:
            return None
        
        # Attach AWS managed policy for Lambda basic execution
        self.attach_policy(role_name, 'arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole')
        
        # Create custom inline policy for SageMaker Model Monitor
        lambda_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        's3:GetObject',
                        's3:PutObject'
                    ],
                    'Resource': [
                        f'arn:aws:s3:::{bucket_name}/monitoring/*'
                    ]
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'sagemaker:CreateMonitoringSchedule',
                        'sagemaker:DescribeMonitoringSchedule',
                        'sagemaker:UpdateMonitoringSchedule',
                        'sagemaker:DescribeEndpoint',
                        'sagemaker:UpdateEndpointWeightsAndCapacities'
                    ],
                    'Resource': '*'
                }
            ]
        }
        
        self.create_inline_policy(role_name, 'LambdaMonitoringAccess', lambda_policy)
        
        return role_arn
    
    def create_step_functions_role(
        self,
        role_name: str,
        lambda_function_arns: list
    ) -> Optional[str]:
        """
        Create Step Functions execution role
        
        Args:
            role_name: Name for the Step Functions role
            lambda_function_arns: List of Lambda function ARN patterns
            
        Returns:
            Role ARN if successful
        """
        print(f"\n--- Creating Step Functions Execution Role ---")
        
        # Trust policy for Step Functions
        assume_role_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Principal': {'Service': 'states.amazonaws.com'},
                'Action': 'sts:AssumeRole'
            }]
        }
        
        role_arn = self.create_role(role_name, assume_role_policy)
        if not role_arn:
            return None
        
        # Create custom inline policy for orchestration
        step_functions_policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': [
                        'sagemaker:CreateProcessingJob',
                        'sagemaker:DescribeProcessingJob',
                        'sagemaker:CreateTrainingJob',
                        'sagemaker:DescribeTrainingJob',
                        'sagemaker:CreateHyperParameterTuningJob',
                        'sagemaker:DescribeHyperParameterTuningJob',
                        'sagemaker:CreateEndpoint',
                        'sagemaker:CreateEndpointConfig',
                        'sagemaker:DescribeEndpoint',
                        'sagemaker:UpdateEndpoint'
                    ],
                    'Resource': '*'
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'lambda:InvokeFunction'
                    ],
                    'Resource': lambda_function_arns
                },
                {
                    'Effect': 'Allow',
                    'Action': [
                        'events:PutTargets',
                        'events:PutRule',
                        'events:DescribeRule'
                    ],
                    'Resource': '*'
                }
            ]
        }
        
        self.create_inline_policy(role_name, 'StepFunctionsOrchestrationAccess', step_functions_policy)
        
        return role_arn
    
    def setup_all_roles(
        self,
        bucket_name: str,
        sagemaker_role_name: str = 'MovieLensSageMakerRole',
        lambda_eval_role_name: str = 'MovieLensLambdaEvaluationRole',
        lambda_monitor_role_name: str = 'MovieLensLambdaMonitoringRole',
        step_functions_role_name: str = 'MovieLensStepFunctionsRole'
    ) -> Dict[str, str]:
        """
        Setup all IAM roles for the ML pipeline
        
        Args:
            bucket_name: S3 bucket name
            sagemaker_role_name: Name for SageMaker role
            lambda_eval_role_name: Name for Lambda evaluation role
            lambda_monitor_role_name: Name for Lambda monitoring role
            step_functions_role_name: Name for Step Functions role
            
        Returns:
            Dictionary mapping role names to ARNs
        """
        print(f"\n=== Setting up IAM Roles ===\n")
        
        roles = {}
        
        # Create SageMaker role
        sagemaker_arn = self.create_sagemaker_execution_role(
            sagemaker_role_name,
            bucket_name
        )
        if sagemaker_arn:
            roles['sagemaker'] = sagemaker_arn
        
        # Create Lambda evaluation role
        lambda_eval_arn = self.create_lambda_evaluation_role(
            lambda_eval_role_name,
            bucket_name
        )
        if lambda_eval_arn:
            roles['lambda_evaluation'] = lambda_eval_arn
        
        # Create Lambda monitoring role
        lambda_monitor_arn = self.create_lambda_monitoring_role(
            lambda_monitor_role_name,
            bucket_name
        )
        if lambda_monitor_arn:
            roles['lambda_monitoring'] = lambda_monitor_arn
        
        # Create Step Functions role
        lambda_arns = [
            f'arn:aws:lambda:*:*:function:movielens-*'
        ]
        step_functions_arn = self.create_step_functions_role(
            step_functions_role_name,
            lambda_arns
        )
        if step_functions_arn:
            roles['step_functions'] = step_functions_arn
        
        print(f"\n✓ Successfully created {len(roles)} IAM roles")
        return roles


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup IAM roles for MovieLens recommendation system')
    parser.add_argument('--bucket-name', required=True, help='Name of the S3 bucket')
    parser.add_argument('--sagemaker-role-name', default='MovieLensSageMakerRole', help='SageMaker role name')
    parser.add_argument('--lambda-eval-role-name', default='MovieLensLambdaEvaluationRole', help='Lambda evaluation role name')
    parser.add_argument('--lambda-monitor-role-name', default='MovieLensLambdaMonitoringRole', help='Lambda monitoring role name')
    parser.add_argument('--step-functions-role-name', default='MovieLensStepFunctionsRole', help='Step Functions role name')
    
    args = parser.parse_args()
    
    setup = IAMSetup()
    roles = setup.setup_all_roles(
        bucket_name=args.bucket_name,
        sagemaker_role_name=args.sagemaker_role_name,
        lambda_eval_role_name=args.lambda_eval_role_name,
        lambda_monitor_role_name=args.lambda_monitor_role_name,
        step_functions_role_name=args.step_functions_role_name
    )
    
    print("\n=== Role ARNs ===")
    for role_type, arn in roles.items():
        print(f"{role_type}: {arn}")
    
    exit(0 if len(roles) == 4 else 1)


if __name__ == '__main__':
    main()
