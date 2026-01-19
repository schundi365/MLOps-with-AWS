"""
Integration tests for IAM role deployment

Tests IAM role creation, policy attachment, and cleanup.
Validates: Requirements 12.1
"""

import pytest
import boto3
import time
import json
from botocore.exceptions import ClientError
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from infrastructure.iam_setup import IAMSetup


@pytest.fixture(scope='module')
def test_bucket_name():
    """Test bucket name for IAM policies"""
    return 'test-movielens-bucket'


@pytest.fixture(scope='module')
def test_role_prefix():
    """Unique prefix for test roles"""
    timestamp = int(time.time())
    return f'TestMovieLens{timestamp}'


@pytest.fixture(scope='module')
def iam_client():
    """IAM client for verification"""
    return boto3.client('iam')


@pytest.fixture(scope='module')
def iam_setup():
    """Create IAMSetup instance"""
    return IAMSetup()


@pytest.fixture(scope='module')
def test_role_names(test_role_prefix):
    """Generate test role names"""
    return {
        'sagemaker': f'{test_role_prefix}SageMaker',
        'lambda_eval': f'{test_role_prefix}LambdaEval',
        'lambda_monitor': f'{test_role_prefix}LambdaMonitor',
        'step_functions': f'{test_role_prefix}StepFunctions'
    }


@pytest.fixture(scope='module', autouse=True)
def cleanup_roles(test_role_names, iam_client):
    """Cleanup test roles after all tests"""
    yield
    
    # Cleanup after tests
    for role_name in test_role_names.values():
        try:
            # Detach managed policies
            response = iam_client.list_attached_role_policies(RoleName=role_name)
            for policy in response.get('AttachedPolicies', []):
                iam_client.detach_role_policy(
                    RoleName=role_name,
                    PolicyArn=policy['PolicyArn']
                )
            
            # Delete inline policies
            response = iam_client.list_role_policies(RoleName=role_name)
            for policy_name in response.get('PolicyNames', []):
                iam_client.delete_role_policy(
                    RoleName=role_name,
                    PolicyName=policy_name
                )
            
            # Delete role
            iam_client.delete_role(RoleName=role_name)
            print(f"\n✓ Cleaned up test role: {role_name}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                print(f"\n✗ Error cleaning up role {role_name}: {e}")


class TestIAMRoleCreation:
    """Test IAM role creation"""
    
    def test_create_sagemaker_role(self, iam_setup, test_role_names, test_bucket_name, iam_client):
        """Test SageMaker execution role creation"""
        role_name = test_role_names['sagemaker']
        
        # Create SageMaker role
        role_arn = iam_setup.create_sagemaker_execution_role(
            role_name=role_name,
            bucket_name=test_bucket_name
        )
        
        assert role_arn is not None, "SageMaker role should be created"
        assert role_name in role_arn, "Role ARN should contain role name"
        
        # Verify role exists
        try:
            response = iam_client.get_role(RoleName=role_name)
            assert response['Role']['RoleName'] == role_name
        except ClientError:
            pytest.fail(f"Role {role_name} should exist")
    
    def test_create_lambda_evaluation_role(self, iam_setup, test_role_names, test_bucket_name, iam_client):
        """Test Lambda evaluation role creation"""
        role_name = test_role_names['lambda_eval']
        
        # Create Lambda evaluation role
        role_arn = iam_setup.create_lambda_evaluation_role(
            role_name=role_name,
            bucket_name=test_bucket_name
        )
        
        assert role_arn is not None, "Lambda evaluation role should be created"
        assert role_name in role_arn, "Role ARN should contain role name"
        
        # Verify role exists
        try:
            response = iam_client.get_role(RoleName=role_name)
            assert response['Role']['RoleName'] == role_name
        except ClientError:
            pytest.fail(f"Role {role_name} should exist")
    
    def test_create_lambda_monitoring_role(self, iam_setup, test_role_names, test_bucket_name, iam_client):
        """Test Lambda monitoring role creation"""
        role_name = test_role_names['lambda_monitor']
        
        # Create Lambda monitoring role
        role_arn = iam_setup.create_lambda_monitoring_role(
            role_name=role_name,
            bucket_name=test_bucket_name
        )
        
        assert role_arn is not None, "Lambda monitoring role should be created"
        assert role_name in role_arn, "Role ARN should contain role name"
        
        # Verify role exists
        try:
            response = iam_client.get_role(RoleName=role_name)
            assert response['Role']['RoleName'] == role_name
        except ClientError:
            pytest.fail(f"Role {role_name} should exist")
    
    def test_create_step_functions_role(self, iam_setup, test_role_names, iam_client):
        """Test Step Functions execution role creation"""
        role_name = test_role_names['step_functions']
        lambda_arns = ['arn:aws:lambda:*:*:function:test-*']
        
        # Create Step Functions role
        role_arn = iam_setup.create_step_functions_role(
            role_name=role_name,
            lambda_function_arns=lambda_arns
        )
        
        assert role_arn is not None, "Step Functions role should be created"
        assert role_name in role_arn, "Role ARN should contain role name"
        
        # Verify role exists
        try:
            response = iam_client.get_role(RoleName=role_name)
            assert response['Role']['RoleName'] == role_name
        except ClientError:
            pytest.fail(f"Role {role_name} should exist")


class TestIAMRolePolicies:
    """Test IAM role policy configuration"""
    
    def test_sagemaker_role_has_policies(self, test_role_names, iam_client):
        """Test SageMaker role has required policies"""
        role_name = test_role_names['sagemaker']
        
        # Check attached managed policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        attached_policies = response.get('AttachedPolicies', [])
        
        # Should have SageMaker managed policy
        policy_names = [p['PolicyName'] for p in attached_policies]
        assert 'AmazonSageMakerFullAccess' in policy_names, "Should have SageMaker managed policy"
        
        # Check inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        inline_policies = response.get('PolicyNames', [])
        assert 'SageMakerS3Access' in inline_policies, "Should have S3 access inline policy"
    
    def test_lambda_evaluation_role_has_policies(self, test_role_names, iam_client):
        """Test Lambda evaluation role has required policies"""
        role_name = test_role_names['lambda_eval']
        
        # Check attached managed policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        attached_policies = response.get('AttachedPolicies', [])
        
        # Should have Lambda basic execution policy
        policy_names = [p['PolicyName'] for p in attached_policies]
        assert 'AWSLambdaBasicExecutionRole' in policy_names, "Should have Lambda basic execution policy"
        
        # Check inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        inline_policies = response.get('PolicyNames', [])
        assert 'LambdaEvaluationAccess' in inline_policies, "Should have evaluation access inline policy"
    
    def test_lambda_monitoring_role_has_policies(self, test_role_names, iam_client):
        """Test Lambda monitoring role has required policies"""
        role_name = test_role_names['lambda_monitor']
        
        # Check attached managed policies
        response = iam_client.list_attached_role_policies(RoleName=role_name)
        attached_policies = response.get('AttachedPolicies', [])
        
        # Should have Lambda basic execution policy
        policy_names = [p['PolicyName'] for p in attached_policies]
        assert 'AWSLambdaBasicExecutionRole' in policy_names, "Should have Lambda basic execution policy"
        
        # Check inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        inline_policies = response.get('PolicyNames', [])
        assert 'LambdaMonitoringAccess' in inline_policies, "Should have monitoring access inline policy"
    
    def test_step_functions_role_has_policies(self, test_role_names, iam_client):
        """Test Step Functions role has required policies"""
        role_name = test_role_names['step_functions']
        
        # Check inline policies
        response = iam_client.list_role_policies(RoleName=role_name)
        inline_policies = response.get('PolicyNames', [])
        assert 'StepFunctionsOrchestrationAccess' in inline_policies, "Should have orchestration access inline policy"


class TestIAMRoleTrustPolicies:
    """Test IAM role trust policies"""
    
    def test_sagemaker_role_trust_policy(self, test_role_names, iam_client):
        """Test SageMaker role has correct trust policy"""
        role_name = test_role_names['sagemaker']
        
        response = iam_client.get_role(RoleName=role_name)
        trust_policy = response['Role']['AssumeRolePolicyDocument']
        
        # Verify SageMaker service can assume role
        statements = trust_policy['Statement']
        assert len(statements) > 0, "Trust policy should have statements"
        
        sagemaker_principals = [
            s for s in statements
            if s.get('Principal', {}).get('Service') == 'sagemaker.amazonaws.com'
        ]
        assert len(sagemaker_principals) > 0, "SageMaker should be able to assume role"
    
    def test_lambda_role_trust_policy(self, test_role_names, iam_client):
        """Test Lambda roles have correct trust policy"""
        for role_key in ['lambda_eval', 'lambda_monitor']:
            role_name = test_role_names[role_key]
            
            response = iam_client.get_role(RoleName=role_name)
            trust_policy = response['Role']['AssumeRolePolicyDocument']
            
            # Verify Lambda service can assume role
            statements = trust_policy['Statement']
            lambda_principals = [
                s for s in statements
                if s.get('Principal', {}).get('Service') == 'lambda.amazonaws.com'
            ]
            assert len(lambda_principals) > 0, f"Lambda should be able to assume {role_name}"
    
    def test_step_functions_role_trust_policy(self, test_role_names, iam_client):
        """Test Step Functions role has correct trust policy"""
        role_name = test_role_names['step_functions']
        
        response = iam_client.get_role(RoleName=role_name)
        trust_policy = response['Role']['AssumeRolePolicyDocument']
        
        # Verify Step Functions service can assume role
        statements = trust_policy['Statement']
        sfn_principals = [
            s for s in statements
            if s.get('Principal', {}).get('Service') == 'states.amazonaws.com'
        ]
        assert len(sfn_principals) > 0, "Step Functions should be able to assume role"


class TestIAMCompleteSetup:
    """Test complete IAM setup"""
    
    def test_setup_all_roles(self, test_bucket_name, test_role_prefix):
        """Test complete IAM role setup"""
        # Create new setup instance for complete test
        setup = IAMSetup()
        
        # Generate unique role names for this test
        timestamp = int(time.time())
        prefix = f'TestComplete{timestamp}'
        
        # Run complete setup
        roles = setup.setup_all_roles(
            bucket_name=test_bucket_name,
            sagemaker_role_name=f'{prefix}SageMaker',
            lambda_eval_role_name=f'{prefix}LambdaEval',
            lambda_monitor_role_name=f'{prefix}LambdaMonitor',
            step_functions_role_name=f'{prefix}StepFunctions'
        )
        
        # Verify all roles created
        assert len(roles) == 4, "All 4 roles should be created"
        assert 'sagemaker' in roles, "SageMaker role should be in results"
        assert 'lambda_evaluation' in roles, "Lambda evaluation role should be in results"
        assert 'lambda_monitoring' in roles, "Lambda monitoring role should be in results"
        assert 'step_functions' in roles, "Step Functions role should be in results"
        
        # Verify all ARNs are valid
        for role_type, arn in roles.items():
            assert arn is not None, f"{role_type} ARN should not be None"
            assert 'arn:aws:iam::' in arn, f"{role_type} ARN should be valid"
        
        # Cleanup these test roles
        iam_client = boto3.client('iam')
        for role_arn in roles.values():
            role_name = role_arn.split('/')[-1]
            try:
                # Detach managed policies
                response = iam_client.list_attached_role_policies(RoleName=role_name)
                for policy in response.get('AttachedPolicies', []):
                    iam_client.detach_role_policy(
                        RoleName=role_name,
                        PolicyArn=policy['PolicyArn']
                    )
                
                # Delete inline policies
                response = iam_client.list_role_policies(RoleName=role_name)
                for policy_name in response.get('PolicyNames', []):
                    iam_client.delete_role_policy(
                        RoleName=role_name,
                        PolicyName=policy_name
                    )
                
                # Delete role
                iam_client.delete_role(RoleName=role_name)
            except ClientError:
                pass
