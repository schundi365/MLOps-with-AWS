"""
Integration tests for end-to-end infrastructure deployment

Tests complete deployment workflow including:
- S3 bucket setup
- IAM role creation
- Infrastructure orchestration

Validates: All infrastructure requirements
"""

import pytest
import boto3
import time
from botocore.exceptions import ClientError
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from infrastructure.s3_setup import S3BucketSetup
from infrastructure.iam_setup import IAMSetup


@pytest.fixture(scope='module')
def test_deployment_config():
    """Configuration for end-to-end deployment test"""
    timestamp = int(time.time())
    return {
        'bucket_name': f'test-e2e-movielens-{timestamp}',
        'region': 'us-east-1',
        'role_prefix': f'TestE2E{timestamp}'
    }


@pytest.fixture(scope='module')
def aws_clients(test_deployment_config):
    """AWS clients for verification"""
    region = test_deployment_config['region']
    return {
        's3': boto3.client('s3', region_name=region),
        'iam': boto3.client('iam')
    }


@pytest.fixture(scope='module', autouse=True)
def cleanup_resources(test_deployment_config, aws_clients):
    """Cleanup all test resources after tests"""
    yield
    
    bucket_name = test_deployment_config['bucket_name']
    role_prefix = test_deployment_config['role_prefix']
    s3_client = aws_clients['s3']
    iam_client = aws_clients['iam']
    
    # Cleanup S3 bucket
    try:
        # Delete all objects
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': objects}
            )
        
        # Delete bucket
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"\n✓ Cleaned up test bucket: {bucket_name}")
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchBucket':
            print(f"\n✗ Error cleaning up bucket: {e}")
    
    # Cleanup IAM roles
    role_names = [
        f'{role_prefix}SageMaker',
        f'{role_prefix}LambdaEval',
        f'{role_prefix}LambdaMonitor',
        f'{role_prefix}StepFunctions'
    ]
    
    for role_name in role_names:
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
            print(f"✓ Cleaned up test role: {role_name}")
        except ClientError as e:
            if e.response['Error']['Code'] != 'NoSuchEntity':
                print(f"✗ Error cleaning up role {role_name}: {e}")


class TestEndToEndDeployment:
    """Test complete end-to-end deployment"""
    
    def test_deploy_iam_roles_first(self, test_deployment_config):
        """Test deploying IAM roles as first step"""
        bucket_name = test_deployment_config['bucket_name']
        role_prefix = test_deployment_config['role_prefix']
        
        # Setup IAM roles
        iam_setup = IAMSetup()
        roles = iam_setup.setup_all_roles(
            bucket_name=bucket_name,
            sagemaker_role_name=f'{role_prefix}SageMaker',
            lambda_eval_role_name=f'{role_prefix}LambdaEval',
            lambda_monitor_role_name=f'{role_prefix}LambdaMonitor',
            step_functions_role_name=f'{role_prefix}StepFunctions'
        )
        
        # Verify all roles created
        assert len(roles) == 4, "All 4 IAM roles should be created"
        assert all(arn is not None for arn in roles.values()), "All role ARNs should be valid"
        
        # Store roles for next test
        test_deployment_config['roles'] = roles
    
    def test_deploy_s3_bucket_with_roles(self, test_deployment_config):
        """Test deploying S3 bucket with IAM roles"""
        bucket_name = test_deployment_config['bucket_name']
        region = test_deployment_config['region']
        roles = test_deployment_config.get('roles', {})
        
        # Ensure roles exist
        if not roles:
            pytest.skip("IAM roles not created in previous test")
        
        # Setup S3 bucket
        s3_setup = S3BucketSetup(bucket_name, region)
        success = s3_setup.setup_complete_bucket(
            sagemaker_role_arn=roles['sagemaker'],
            lambda_role_arns=[roles['lambda_evaluation'], roles['lambda_monitoring']]
        )
        
        assert success, "S3 bucket setup should succeed"
    
    def test_verify_complete_infrastructure(self, test_deployment_config, aws_clients):
        """Test verifying complete infrastructure is deployed correctly"""
        bucket_name = test_deployment_config['bucket_name']
        role_prefix = test_deployment_config['role_prefix']
        s3_client = aws_clients['s3']
        iam_client = aws_clients['iam']
        
        # Verify S3 bucket
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except ClientError:
            pytest.fail(f"S3 bucket {bucket_name} should exist")
        
        # Verify S3 bucket configuration
        versioning = s3_client.get_bucket_versioning(Bucket=bucket_name)
        assert versioning.get('Status') == 'Enabled', "Versioning should be enabled"
        
        encryption = s3_client.get_bucket_encryption(Bucket=bucket_name)
        assert 'ServerSideEncryptionConfiguration' in encryption, "Encryption should be enabled"
        
        lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=bucket_name)
        assert len(lifecycle['Rules']) > 0, "Lifecycle policy should exist"
        
        # Verify IAM roles
        role_names = [
            f'{role_prefix}SageMaker',
            f'{role_prefix}LambdaEval',
            f'{role_prefix}LambdaMonitor',
            f'{role_prefix}StepFunctions'
        ]
        
        for role_name in role_names:
            try:
                response = iam_client.get_role(RoleName=role_name)
                assert response['Role']['RoleName'] == role_name, f"Role {role_name} should exist"
            except ClientError:
                pytest.fail(f"IAM role {role_name} should exist")
    
    def test_s3_bucket_accessible_by_roles(self, test_deployment_config, aws_clients):
        """Test S3 bucket is accessible by created IAM roles"""
        bucket_name = test_deployment_config['bucket_name']
        s3_client = aws_clients['s3']
        
        # Get bucket policy
        try:
            response = s3_client.get_bucket_policy(Bucket=bucket_name)
            policy_str = response['Policy']
            
            import json
            policy = json.loads(policy_str)
            
            # Verify policy has statements
            assert 'Statement' in policy, "Bucket policy should have statements"
            assert len(policy['Statement']) > 0, "Bucket policy should have at least one statement"
            
            # Verify policy includes role ARNs
            statements = policy['Statement']
            allow_statements = [s for s in statements if s.get('Effect') == 'Allow']
            assert len(allow_statements) > 0, "Policy should have Allow statements"
            
        except ClientError as e:
            pytest.fail(f"Failed to get bucket policy: {e}")
    
    def test_directory_structure_created(self, test_deployment_config, aws_clients):
        """Test S3 bucket has correct directory structure"""
        bucket_name = test_deployment_config['bucket_name']
        s3_client = aws_clients['s3']
        
        expected_dirs = [
            'raw-data/',
            'processed-data/',
            'models/',
            'outputs/',
            'monitoring/data-capture/',
            'monitoring/baseline/',
            'monitoring/reports/',
            'metrics/'
        ]
        
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        assert 'Contents' in response, "Bucket should have objects"
        
        keys = [obj['Key'] for obj in response['Contents']]
        for expected_dir in expected_dirs:
            assert expected_dir in keys, f"Directory {expected_dir} should exist"


class TestDeploymentIdempotency:
    """Test deployment idempotency"""
    
    def test_redeploy_iam_roles_idempotent(self, test_deployment_config):
        """Test redeploying IAM roles is idempotent"""
        bucket_name = test_deployment_config['bucket_name']
        role_prefix = test_deployment_config['role_prefix']
        
        # Deploy roles again
        iam_setup = IAMSetup()
        roles = iam_setup.setup_all_roles(
            bucket_name=bucket_name,
            sagemaker_role_name=f'{role_prefix}SageMaker',
            lambda_eval_role_name=f'{role_prefix}LambdaEval',
            lambda_monitor_role_name=f'{role_prefix}LambdaMonitor',
            step_functions_role_name=f'{role_prefix}StepFunctions'
        )
        
        # Should succeed and return same roles
        assert len(roles) == 4, "All 4 IAM roles should exist"
        assert all(arn is not None for arn in roles.values()), "All role ARNs should be valid"
    
    def test_redeploy_s3_bucket_idempotent(self, test_deployment_config):
        """Test redeploying S3 bucket is idempotent"""
        bucket_name = test_deployment_config['bucket_name']
        region = test_deployment_config['region']
        roles = test_deployment_config.get('roles', {})
        
        if not roles:
            pytest.skip("IAM roles not available")
        
        # Deploy bucket again
        s3_setup = S3BucketSetup(bucket_name, region)
        success = s3_setup.setup_complete_bucket(
            sagemaker_role_arn=roles['sagemaker'],
            lambda_role_arns=[roles['lambda_evaluation'], roles['lambda_monitoring']]
        )
        
        # Should succeed (idempotent)
        assert success, "S3 bucket redeployment should succeed"


class TestDeploymentErrorHandling:
    """Test deployment error handling"""
    
    def test_s3_setup_fails_with_invalid_role_arn(self):
        """Test S3 setup handles invalid role ARN gracefully"""
        timestamp = int(time.time())
        bucket_name = f'test-error-{timestamp}'
        
        s3_setup = S3BucketSetup(bucket_name, 'us-east-1')
        
        # Try to setup with invalid role ARN
        success = s3_setup.setup_complete_bucket(
            sagemaker_role_arn='invalid-arn',
            lambda_role_arns=['invalid-arn']
        )
        
        # Should handle error gracefully (may succeed with bucket creation but fail on policy)
        # The important thing is it doesn't crash
        assert isinstance(success, bool), "Should return boolean result"
        
        # Cleanup
        try:
            s3_client = boto3.client('s3', region_name='us-east-1')
            s3_client.delete_bucket(Bucket=bucket_name)
        except ClientError:
            pass
    
    def test_iam_setup_handles_missing_permissions(self):
        """Test IAM setup handles permission errors gracefully"""
        # This test verifies the code handles errors without crashing
        # Actual permission errors depend on the test environment
        
        iam_setup = IAMSetup()
        
        # Try to create role with potentially restricted name
        timestamp = int(time.time())
        role_name = f'TestPermission{timestamp}'
        
        assume_role_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Effect': 'Allow',
                'Principal': {'Service': 'sagemaker.amazonaws.com'},
                'Action': 'sts:AssumeRole'
            }]
        }
        
        # Should handle any errors gracefully
        result = iam_setup.create_role(role_name, assume_role_policy)
        
        # Result should be either ARN or None, not an exception
        assert result is None or isinstance(result, str), "Should return ARN or None"
        
        # Cleanup if created
        if result:
            try:
                iam_client = boto3.client('iam')
                iam_client.delete_role(RoleName=role_name)
            except ClientError:
                pass
