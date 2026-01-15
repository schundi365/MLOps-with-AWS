"""
EventBridge Deployment Script for MovieLens Recommendation System

This script deploys EventBridge scheduled rules for:
- Weekly automated model retraining
- Step Functions state machine triggering

Requirements: 11.1, 11.2
"""

import boto3
import json
from typing import Optional
from datetime import datetime
from botocore.exceptions import ClientError


class EventBridgeDeployment:
    """Manages EventBridge rule deployment for scheduled retraining"""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize EventBridge deployment
        
        Args:
            region: AWS region
        """
        self.region = region
        self.events_client = boto3.client('events', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
    def create_scheduled_rule(
        self,
        rule_name: str,
        schedule_expression: str,
        description: str = None
    ) -> bool:
        """
        Create EventBridge scheduled rule
        
        Args:
            rule_name: Name for the rule
            schedule_expression: Cron or rate expression
            description: Optional description
            
        Returns:
            True if rule created successfully
        """
        try:
            response = self.events_client.put_rule(
                Name=rule_name,
                ScheduleExpression=schedule_expression,
                State='ENABLED',
                Description=description or f'Scheduled rule: {rule_name}'
            )
            
            print(f"✓ Created scheduled rule: {rule_name}")
            print(f"  Schedule: {schedule_expression}")
            return True
            
        except ClientError as e:
            print(f"✗ Error creating scheduled rule: {e}")
            return False
    
    def add_step_functions_target(
        self,
        rule_name: str,
        state_machine_arn: str,
        role_arn: str,
        input_template: dict = None
    ) -> bool:
        """
        Add Step Functions state machine as target for EventBridge rule
        
        Args:
            rule_name: Name of the EventBridge rule
            state_machine_arn: ARN of the Step Functions state machine
            role_arn: IAM role ARN for EventBridge to invoke Step Functions
            input_template: Optional input template for state machine execution
            
        Returns:
            True if target added successfully
        """
        try:
            # Default input template with timestamp-based job names
            if input_template is None:
                input_template = {
                    "preprocessing_job_name": f"movielens-preprocessing-<aws.events.rule-name>-<aws.events.time>",
                    "training_job_name": f"movielens-training-<aws.events.rule-name>-<aws.events.time>",
                    "endpoint_name": "movielens-recommendation-endpoint",
                    "endpoint_config_name": f"movielens-endpoint-config-<aws.events.time>"
                }
            
            # Add target
            response = self.events_client.put_targets(
                Rule=rule_name,
                Targets=[
                    {
                        'Id': '1',
                        'Arn': state_machine_arn,
                        'RoleArn': role_arn,
                        'Input': json.dumps(input_template)
                    }
                ]
            )
            
            if response['FailedEntryCount'] == 0:
                print(f"✓ Added Step Functions target to rule: {rule_name}")
                return True
            else:
                print(f"✗ Failed to add target: {response['FailedEntries']}")
                return False
                
        except ClientError as e:
            print(f"✗ Error adding target to rule: {e}")
            return False
    
    def create_eventbridge_role_policy(
        self,
        state_machine_arn: str
    ) -> dict:
        """
        Create IAM policy document for EventBridge to invoke Step Functions
        
        Args:
            state_machine_arn: ARN of the Step Functions state machine
            
        Returns:
            Policy document as dictionary
        """
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Action': 'states:StartExecution',
                    'Resource': state_machine_arn
                }
            ]
        }
        return policy
    
    def deploy_weekly_retraining_schedule(
        self,
        rule_name: str,
        state_machine_arn: str,
        eventbridge_role_arn: str,
        schedule: str = 'cron(0 2 ? * SUN *)'
    ) -> bool:
        """
        Deploy weekly retraining schedule
        
        Args:
            rule_name: Name for the EventBridge rule
            state_machine_arn: ARN of the ML pipeline state machine
            eventbridge_role_arn: IAM role ARN for EventBridge
            schedule: Cron expression (default: Sunday 2 AM UTC)
            
        Returns:
            True if deployment successful
        """
        print(f"\n=== Deploying EventBridge Scheduled Retraining ===\n")
        
        # Create scheduled rule
        rule_success = self.create_scheduled_rule(
            rule_name=rule_name,
            schedule_expression=schedule,
            description='Weekly automated model retraining for MovieLens recommendation system'
        )
        
        if not rule_success:
            return False
        
        # Add Step Functions target
        target_success = self.add_step_functions_target(
            rule_name=rule_name,
            state_machine_arn=state_machine_arn,
            role_arn=eventbridge_role_arn
        )
        
        if target_success:
            print(f"\n✓ Successfully deployed weekly retraining schedule")
            print(f"Rule: {rule_name}")
            print(f"Schedule: {schedule}")
            print(f"Target: {state_machine_arn}")
        
        return target_success
    
    def create_eventbridge_execution_role(
        self,
        role_name: str,
        state_machine_arn: str
    ) -> Optional[str]:
        """
        Create IAM role for EventBridge to invoke Step Functions
        
        Args:
            role_name: Name for the IAM role
            state_machine_arn: ARN of the Step Functions state machine
            
        Returns:
            Role ARN if successful
        """
        iam_client = boto3.client('iam')
        
        try:
            # Trust policy for EventBridge
            assume_role_policy = {
                'Version': '2012-10-17',
                'Statement': [{
                    'Effect': 'Allow',
                    'Principal': {'Service': 'events.amazonaws.com'},
                    'Action': 'sts:AssumeRole'
                }]
            }
            
            # Create role
            try:
                response = iam_client.create_role(
                    RoleName=role_name,
                    AssumeRolePolicyDocument=json.dumps(assume_role_policy),
                    Description='EventBridge role to invoke Step Functions for scheduled retraining'
                )
                role_arn = response['Role']['Arn']
                print(f"✓ Created EventBridge role: {role_name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'EntityAlreadyExists':
                    response = iam_client.get_role(RoleName=role_name)
                    role_arn = response['Role']['Arn']
                    print(f"✓ EventBridge role already exists: {role_name}")
                else:
                    raise
            
            # Create inline policy
            policy_document = self.create_eventbridge_role_policy(state_machine_arn)
            iam_client.put_role_policy(
                RoleName=role_name,
                PolicyName='EventBridgeStepFunctionsAccess',
                PolicyDocument=json.dumps(policy_document)
            )
            print(f"✓ Created inline policy for EventBridge role")
            
            return role_arn
            
        except ClientError as e:
            print(f"✗ Error creating EventBridge role: {e}")
            return None
    
    def deploy_complete_schedule(
        self,
        rule_name: str,
        state_machine_arn: str,
        eventbridge_role_name: str = 'MovieLensEventBridgeRole',
        schedule: str = 'cron(0 2 ? * SUN *)'
    ) -> bool:
        """
        Deploy complete scheduled retraining with role creation
        
        Args:
            rule_name: Name for the EventBridge rule
            state_machine_arn: ARN of the ML pipeline state machine
            eventbridge_role_name: Name for the EventBridge IAM role
            schedule: Cron expression
            
        Returns:
            True if deployment successful
        """
        # Create EventBridge execution role
        role_arn = self.create_eventbridge_execution_role(
            role_name=eventbridge_role_name,
            state_machine_arn=state_machine_arn
        )
        
        if not role_arn:
            return False
        
        # Deploy scheduled rule with target
        return self.deploy_weekly_retraining_schedule(
            rule_name=rule_name,
            state_machine_arn=state_machine_arn,
            eventbridge_role_arn=role_arn,
            schedule=schedule
        )


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy EventBridge scheduled retraining for MovieLens recommendation system')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--rule-name', default='MovieLensWeeklyRetraining', help='EventBridge rule name')
    parser.add_argument('--state-machine-arn', required=True, help='Step Functions state machine ARN')
    parser.add_argument('--eventbridge-role-name', default='MovieLensEventBridgeRole', help='EventBridge IAM role name')
    parser.add_argument('--schedule', default='cron(0 2 ? * SUN *)', help='Cron schedule expression')
    
    args = parser.parse_args()
    
    deployment = EventBridgeDeployment(args.region)
    success = deployment.deploy_complete_schedule(
        rule_name=args.rule_name,
        state_machine_arn=args.state_machine_arn,
        eventbridge_role_name=args.eventbridge_role_name,
        schedule=args.schedule
    )
    
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
