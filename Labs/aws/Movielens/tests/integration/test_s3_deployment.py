"""
Integration tests for S3 bucket deployment

Tests S3 bucket creation, configuration, and cleanup.
Validates: Requirements 1.2, 1.4, 1.5, 1.6, 12.6
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


@pytest.fixture(scope='module')
def test_bucket_name():
    """Generate unique test bucket name"""
    timestamp = int(time.time())
    return f'test-movielens-{timestamp}'


@pytest.fixture(scope='module')
def aws_region():
    """AWS region for testing"""
    return 'us-east-1'


@pytest.fixture(scope='module')
def s3_client(aws_region):
    """S3 client for verification"""
    return boto3.client('s3', region_name=aws_region)


@pytest.fixture(scope='module')
def test_role_arns():
    """Mock role ARNs for testing"""
    return {
        'sagemaker': 'arn:aws:iam::123456789012:role/TestSageMakerRole',
        'lambda': ['arn:aws:iam::123456789012:role/TestLambdaRole']
    }


@pytest.fixture(scope='module')
def s3_setup(test_bucket_name, aws_region):
    """Create S3BucketSetup instance"""
    return S3BucketSetup(test_bucket_name, aws_region)


@pytest.fixture(scope='module', autouse=True)
def cleanup_bucket(test_bucket_name, s3_client):
    """Cleanup test bucket after all tests"""
    yield
    
    # Cleanup after tests
    try:
        # Delete all objects in bucket
        response = s3_client.list_objects_v2(Bucket=test_bucket_name)
        if 'Contents' in response:
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            s3_client.delete_objects(
                Bucket=test_bucket_name,
                Delete={'Objects': objects}
            )
        
        # Delete bucket
        s3_client.delete_bucket(Bucket=test_bucket_name)
        print(f"\n✓ Cleaned up test bucket: {test_bucket_name}")
    except ClientError as e:
        if e.response['Error']['Code'] != 'NoSuchBucket':
            print(f"\n✗ Error cleaning up bucket: {e}")


class TestS3BucketCreation:
    """Test S3 bucket creation"""
    
    def test_create_bucket(self, s3_setup, s3_client, test_bucket_name):
        """Test S3 bucket creation"""
        # Create bucket
        success = s3_setup.create_bucket()
        assert success, "Bucket creation should succeed"
        
        # Verify bucket exists
        try:
            s3_client.head_bucket(Bucket=test_bucket_name)
        except ClientError:
            pytest.fail(f"Bucket {test_bucket_name} should exist")
    
    def test_create_bucket_idempotent(self, s3_setup):
        """Test that creating bucket twice is idempotent"""
        # Create bucket again
        success = s3_setup.create_bucket()
        assert success, "Creating existing bucket should succeed (idempotent)"


class TestS3BucketConfiguration:
    """Test S3 bucket configuration"""
    
    def test_enable_versioning(self, s3_setup, s3_client, test_bucket_name):
        """Test enabling versioning on bucket"""
        # Enable versioning
        success = s3_setup.enable_versioning()
        assert success, "Versioning should be enabled successfully"
        
        # Verify versioning is enabled
        response = s3_client.get_bucket_versioning(Bucket=test_bucket_name)
        assert response.get('Status') == 'Enabled', "Versioning should be enabled"
    
    def test_enable_encryption(self, s3_setup, s3_client, test_bucket_name):
        """Test enabling encryption on bucket"""
        # Enable encryption (SSE-S3)
        success = s3_setup.enable_encryption()
        assert success, "Encryption should be enabled successfully"
        
        # Verify encryption is enabled
        response = s3_client.get_bucket_encryption(Bucket=test_bucket_name)
        rules = response['ServerSideEncryptionConfiguration']['Rules']
        assert len(rules) > 0, "Encryption rules should exist"
        assert rules[0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] == 'AES256'
    
    def test_configure_lifecycle_policy(self, s3_setup, s3_client, test_bucket_name):
        """Test configuring lifecycle policy"""
        # Configure lifecycle policy
        success = s3_setup.configure_lifecycle_policy(days_to_glacier=90)
        assert success, "Lifecycle policy should be configured successfully"
        
        # Verify lifecycle policy exists
        response = s3_client.get_bucket_lifecycle_configuration(Bucket=test_bucket_name)
        rules = response['Rules']
        assert len(rules) > 0, "Lifecycle rules should exist"
        assert rules[0]['Status'] == 'Enabled'
        assert rules[0]['Transitions'][0]['Days'] == 90
        assert rules[0]['Transitions'][0]['StorageClass'] == 'GLACIER'
    
    def test_create_directory_structure(self, s3_setup, s3_client, test_bucket_name):
        """Test creating directory structure in bucket"""
        # Create directory structure
        success = s3_setup.create_directory_structure()
        assert success, "Directory structure should be created successfully"
        
        # Verify directories exist
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
        
        response = s3_client.list_objects_v2(Bucket=test_bucket_name)
        if 'Contents' in response:
            keys = [obj['Key'] for obj in response['Contents']]
            for expected_dir in expected_dirs:
                assert expected_dir in keys, f"Directory {expected_dir} should exist"


class TestS3BucketPolicy:
    """Test S3 bucket policy configuration"""
    
    def test_set_bucket_policy(self, s3_setup, s3_client, test_bucket_name, test_role_arns):
        """Test setting bucket policy"""
        # Set bucket policy
        success = s3_setup.set_bucket_policy(
            sagemaker_role_arn=test_role_arns['sagemaker'],
            lambda_role_arns=test_role_arns['lambda']
        )
        assert success, "Bucket policy should be set successfully"
        
        # Verify bucket policy exists
        try:
            response = s3_client.get_bucket_policy(Bucket=test_bucket_name)
            assert 'Policy' in response, "Bucket policy should exist"
            
            import json
            policy = json.loads(response['Policy'])
            assert 'Statement' in policy, "Policy should have statements"
            assert len(policy['Statement']) >= 2, "Policy should have multiple statements"
        except ClientError as e:
            pytest.fail(f"Failed to get bucket policy: {e}")


class TestS3CompleteSetup:
    """Test complete S3 bucket setup"""
    
    def test_setup_complete_bucket(self, test_bucket_name, aws_region, test_role_arns):
        """Test complete bucket setup with all configurations"""
        # Create new setup instance for complete test
        setup = S3BucketSetup(test_bucket_name, aws_region)
        
        # Run complete setup
        success = setup.setup_complete_bucket(
            sagemaker_role_arn=test_role_arns['sagemaker'],
            lambda_role_arns=test_role_arns['lambda'],
            days_to_glacier=90
        )
        
        assert success, "Complete bucket setup should succeed"
        
        # Verify all configurations are in place
        s3_client = boto3.client('s3', region_name=aws_region)
        
        # Check bucket exists
        try:
            s3_client.head_bucket(Bucket=test_bucket_name)
        except ClientError:
            pytest.fail(f"Bucket {test_bucket_name} should exist")
        
        # Check versioning
        versioning = s3_client.get_bucket_versioning(Bucket=test_bucket_name)
        assert versioning.get('Status') == 'Enabled', "Versioning should be enabled"
        
        # Check encryption
        encryption = s3_client.get_bucket_encryption(Bucket=test_bucket_name)
        assert 'ServerSideEncryptionConfiguration' in encryption
        
        # Check lifecycle policy
        lifecycle = s3_client.get_bucket_lifecycle_configuration(Bucket=test_bucket_name)
        assert len(lifecycle['Rules']) > 0
        
        # Check directory structure
        objects = s3_client.list_objects_v2(Bucket=test_bucket_name)
        assert 'Contents' in objects, "Directory structure should exist"
