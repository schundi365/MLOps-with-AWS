"""
S3 Bucket Setup Script for MovieLens Recommendation System

This script creates and configures the S3 bucket with:
- Proper naming convention
- Versioning enabled
- Server-side encryption
- Lifecycle policies for archiving
- Bucket policies for access control

Requirements: 1.2, 1.4, 1.5, 1.6, 12.6
"""

import boto3
import json
from typing import Dict, Optional
from botocore.exceptions import ClientError


class S3BucketSetup:
    """Manages S3 bucket creation and configuration for the ML pipeline"""
    
    def __init__(self, bucket_name: str, region: str = 'us-east-1'):
        """
        Initialize S3 bucket setup
        
        Args:
            bucket_name: Name of the S3 bucket to create
            region: AWS region for the bucket
        """
        self.bucket_name = bucket_name
        self.region = region
        self.s3_client = boto3.client('s3', region_name=region)
        
    def create_bucket(self) -> bool:
        """
        Create S3 bucket with proper naming
        
        Returns:
            True if bucket created successfully, False otherwise
        """
        try:
            if self.region == 'us-east-1':
                # us-east-1 doesn't require LocationConstraint
                self.s3_client.create_bucket(Bucket=self.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=self.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': self.region}
                )
            print(f"✓ Created bucket: {self.bucket_name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
                print(f"✓ Bucket already exists: {self.bucket_name}")
                return True
            else:
                print(f"✗ Error creating bucket: {e}")
                return False
    
    def enable_versioning(self) -> bool:
        """
        Enable versioning for data lineage tracking
        
        Returns:
            True if versioning enabled successfully
        """
        try:
            self.s3_client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={'Status': 'Enabled'}
            )
            print(f"✓ Enabled versioning on bucket: {self.bucket_name}")
            return True
        except ClientError as e:
            print(f"✗ Error enabling versioning: {e}")
            return False
    
    def enable_encryption(self, kms_key_id: Optional[str] = None) -> bool:
        """
        Enable server-side encryption (SSE-S3 or SSE-KMS)
        
        Args:
            kms_key_id: Optional KMS key ID for SSE-KMS encryption
            
        Returns:
            True if encryption enabled successfully
        """
        try:
            if kms_key_id:
                # Use SSE-KMS with customer-managed key
                encryption_config = {
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'aws:kms',
                            'KMSMasterKeyID': kms_key_id
                        },
                        'BucketKeyEnabled': True
                    }]
                }
            else:
                # Use SSE-S3 (default AWS-managed encryption)
                encryption_config = {
                    'Rules': [{
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        }
                    }]
                }
            
            self.s3_client.put_bucket_encryption(
                Bucket=self.bucket_name,
                ServerSideEncryptionConfiguration=encryption_config
            )
            encryption_type = 'SSE-KMS' if kms_key_id else 'SSE-S3'
            print(f"✓ Enabled {encryption_type} encryption on bucket: {self.bucket_name}")
            return True
        except ClientError as e:
            print(f"✗ Error enabling encryption: {e}")
            return False
    
    def configure_lifecycle_policy(self, days_to_glacier: int = 90) -> bool:
        """
        Configure lifecycle policy to archive old data to Glacier
        
        Args:
            days_to_glacier: Number of days before transitioning to Glacier
            
        Returns:
            True if lifecycle policy configured successfully
        """
        try:
            lifecycle_policy = {
                'Rules': [
                    {
                        'ID': 'ArchiveOldData',
                        'Status': 'Enabled',
                        'Filter': {'Prefix': ''},
                        'Transitions': [
                            {
                                'Days': days_to_glacier,
                                'StorageClass': 'GLACIER'
                            }
                        ]
                    }
                ]
            }
            
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=self.bucket_name,
                LifecycleConfiguration=lifecycle_policy
            )
            print(f"✓ Configured lifecycle policy: archive to Glacier after {days_to_glacier} days")
            return True
        except ClientError as e:
            print(f"✗ Error configuring lifecycle policy: {e}")
            return False
    
    def set_bucket_policy(self, sagemaker_role_arn: str, lambda_role_arns: list) -> bool:
        """
        Set bucket policy for least-privilege access control
        
        Args:
            sagemaker_role_arn: ARN of SageMaker execution role
            lambda_role_arns: List of Lambda execution role ARNs
            
        Returns:
            True if bucket policy set successfully
        """
        try:
            # Combine all authorized role ARNs
            authorized_principals = [sagemaker_role_arn] + lambda_role_arns
            
            bucket_policy = {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Sid': 'AllowSageMakerAndLambdaAccess',
                        'Effect': 'Allow',
                        'Principal': {
                            'AWS': authorized_principals
                        },
                        'Action': [
                            's3:GetObject',
                            's3:PutObject',
                            's3:DeleteObject',
                            's3:ListBucket'
                        ],
                        'Resource': [
                            f'arn:aws:s3:::{self.bucket_name}',
                            f'arn:aws:s3:::{self.bucket_name}/*'
                        ]
                    },
                    {
                        'Sid': 'DenyInsecureTransport',
                        'Effect': 'Deny',
                        'Principal': '*',
                        'Action': 's3:*',
                        'Resource': [
                            f'arn:aws:s3:::{self.bucket_name}',
                            f'arn:aws:s3:::{self.bucket_name}/*'
                        ],
                        'Condition': {
                            'Bool': {
                                'aws:SecureTransport': 'false'
                            }
                        }
                    }
                ]
            }
            
            self.s3_client.put_bucket_policy(
                Bucket=self.bucket_name,
                Policy=json.dumps(bucket_policy)
            )
            print(f"✓ Set bucket policy with least-privilege access")
            return True
        except ClientError as e:
            print(f"✗ Error setting bucket policy: {e}")
            return False
    
    def create_directory_structure(self) -> bool:
        """
        Create organized directory structure in the bucket
        
        Returns:
            True if directories created successfully
        """
        directories = [
            'raw-data/',
            'processed-data/',
            'models/',
            'outputs/',
            'monitoring/data-capture/',
            'monitoring/baseline/',
            'monitoring/reports/',
            'metrics/'
        ]
        
        try:
            for directory in directories:
                # Create empty object to represent directory
                self.s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=directory,
                    Body=b''
                )
            print(f"✓ Created directory structure in bucket")
            return True
        except ClientError as e:
            print(f"✗ Error creating directory structure: {e}")
            return False
    
    def setup_complete_bucket(
        self,
        sagemaker_role_arn: str,
        lambda_role_arns: list,
        kms_key_id: Optional[str] = None,
        days_to_glacier: int = 90
    ) -> bool:
        """
        Complete bucket setup with all configurations
        
        Args:
            sagemaker_role_arn: ARN of SageMaker execution role
            lambda_role_arns: List of Lambda execution role ARNs
            kms_key_id: Optional KMS key ID for encryption
            days_to_glacier: Days before archiving to Glacier
            
        Returns:
            True if all setup steps completed successfully
        """
        print(f"\n=== Setting up S3 bucket: {self.bucket_name} ===\n")
        
        steps = [
            ('Create bucket', lambda: self.create_bucket()),
            ('Enable versioning', lambda: self.enable_versioning()),
            ('Enable encryption', lambda: self.enable_encryption(kms_key_id)),
            ('Configure lifecycle policy', lambda: self.configure_lifecycle_policy(days_to_glacier)),
            ('Set bucket policy', lambda: self.set_bucket_policy(sagemaker_role_arn, lambda_role_arns)),
            ('Create directory structure', lambda: self.create_directory_structure())
        ]
        
        all_success = True
        for step_name, step_func in steps:
            if not step_func():
                all_success = False
                print(f"✗ Failed: {step_name}")
        
        if all_success:
            print(f"\n✓ Successfully completed S3 bucket setup!")
        else:
            print(f"\n✗ Some setup steps failed. Please review errors above.")
        
        return all_success


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Setup S3 bucket for MovieLens recommendation system')
    parser.add_argument('--bucket-name', required=True, help='Name of the S3 bucket')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--sagemaker-role-arn', required=True, help='SageMaker execution role ARN')
    parser.add_argument('--lambda-role-arns', nargs='+', required=True, help='Lambda execution role ARNs')
    parser.add_argument('--kms-key-id', help='Optional KMS key ID for encryption')
    parser.add_argument('--days-to-glacier', type=int, default=90, help='Days before archiving to Glacier')
    
    args = parser.parse_args()
    
    setup = S3BucketSetup(args.bucket_name, args.region)
    success = setup.setup_complete_bucket(
        sagemaker_role_arn=args.sagemaker_role_arn,
        lambda_role_arns=args.lambda_role_arns,
        kms_key_id=args.kms_key_id,
        days_to_glacier=args.days_to_glacier
    )
    
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
