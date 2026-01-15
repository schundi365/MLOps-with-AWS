"""
SageMaker Components Deployment Script for MovieLens Recommendation System

This script deploys SageMaker components:
- Processing jobs for data preprocessing
- Training jobs for model training
- Hyperparameter tuning jobs
- Model endpoints for inference

Requirements: 3.3, 4.1, 4.2, 4.3, 4.4, 5.4, 5.5
"""

import boto3
import time
from typing import Dict, Optional
from datetime import datetime
from botocore.exceptions import ClientError


class SageMakerDeployment:
    """Manages SageMaker component deployment"""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize SageMaker deployment
        
        Args:
            region: AWS region
        """
        self.region = region
        self.sagemaker_client = boto3.client('sagemaker', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
    def create_processing_job(
        self,
        job_name: str,
        role_arn: str,
        bucket_name: str,
        instance_type: str = 'ml.m5.xlarge',
        instance_count: int = 1
    ) -> bool:
        """
        Create SageMaker Processing job for data preprocessing
        
        Args:
            job_name: Unique name for the processing job
            role_arn: IAM role ARN for SageMaker
            bucket_name: S3 bucket name
            instance_type: EC2 instance type
            instance_count: Number of instances
            
        Returns:
            True if job created successfully
        """
        try:
            # Container image for processing
            image_uri = f'683313688378.dkr.ecr.{self.region}.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3'
            
            response = self.sagemaker_client.create_processing_job(
                ProcessingJobName=job_name,
                RoleArn=role_arn,
                ProcessingInputs=[
                    {
                        'InputName': 'raw-data',
                        'S3Input': {
                            'S3Uri': f's3://{bucket_name}/raw-data/',
                            'LocalPath': '/opt/ml/processing/input',
                            'S3DataType': 'S3Prefix',
                            'S3InputMode': 'File'
                        }
                    }
                ],
                ProcessingOutputConfig={
                    'Outputs': [
                        {
                            'OutputName': 'processed-data',
                            'S3Output': {
                                'S3Uri': f's3://{bucket_name}/processed-data/',
                                'LocalPath': '/opt/ml/processing/output',
                                'S3UploadMode': 'EndOfJob'
                            }
                        }
                    ]
                },
                ProcessingResources={
                    'ClusterConfig': {
                        'InstanceCount': instance_count,
                        'InstanceType': instance_type,
                        'VolumeSizeInGB': 30
                    }
                },
                AppSpecification={
                    'ImageUri': image_uri,
                    'ContainerEntrypoint': ['python3', '/opt/ml/processing/input/preprocessing.py']
                },
                StoppingCondition={
                    'MaxRuntimeInSeconds': 3600
                }
            )
            
            print(f"✓ Created processing job: {job_name}")
            return True
        except ClientError as e:
            print(f"✗ Error creating processing job: {e}")
            return False
    
    def create_training_job(
        self,
        job_name: str,
        role_arn: str,
        bucket_name: str,
        hyperparameters: Dict[str, str],
        instance_type: str = 'ml.p3.2xlarge',
        instance_count: int = 1
    ) -> bool:
        """
        Create SageMaker Training job
        
        Args:
            job_name: Unique name for the training job
            role_arn: IAM role ARN for SageMaker
            bucket_name: S3 bucket name
            hyperparameters: Training hyperparameters
            instance_type: EC2 instance type (GPU recommended)
            instance_count: Number of instances
            
        Returns:
            True if job created successfully
        """
        try:
            # PyTorch container image
            image_uri = f'763104351884.dkr.ecr.{self.region}.amazonaws.com/pytorch-training:2.0.0-gpu-py310'
            
            response = self.sagemaker_client.create_training_job(
                TrainingJobName=job_name,
                RoleArn=role_arn,
                AlgorithmSpecification={
                    'TrainingImage': image_uri,
                    'TrainingInputMode': 'File',
                    'EnableSageMakerMetricsTimeSeries': True,
                    'MetricDefinitions': [
                        {
                            'Name': 'train:rmse',
                            'Regex': 'Train RMSE: ([0-9\\.]+)'
                        },
                        {
                            'Name': 'val:rmse',
                            'Regex': 'Val RMSE: ([0-9\\.]+)'
                        }
                    ]
                },
                HyperParameters=hyperparameters,
                InputDataConfig=[
                    {
                        'ChannelName': 'train',
                        'DataSource': {
                            'S3DataSource': {
                                'S3DataType': 'S3Prefix',
                                'S3Uri': f's3://{bucket_name}/processed-data/train.csv',
                                'S3DataDistributionType': 'FullyReplicated'
                            }
                        },
                        'ContentType': 'text/csv'
                    },
                    {
                        'ChannelName': 'validation',
                        'DataSource': {
                            'S3DataSource': {
                                'S3DataType': 'S3Prefix',
                                'S3Uri': f's3://{bucket_name}/processed-data/validation.csv',
                                'S3DataDistributionType': 'FullyReplicated'
                            }
                        },
                        'ContentType': 'text/csv'
                    }
                ],
                OutputDataConfig={
                    'S3OutputPath': f's3://{bucket_name}/models/'
                },
                ResourceConfig={
                    'InstanceType': instance_type,
                    'InstanceCount': instance_count,
                    'VolumeSizeInGB': 50
                },
                StoppingCondition={
                    'MaxRuntimeInSeconds': 86400  # 24 hours
                }
            )
            
            print(f"✓ Created training job: {job_name}")
            return True
        except ClientError as e:
            print(f"✗ Error creating training job: {e}")
            return False
    
    def create_hyperparameter_tuning_job(
        self,
        tuning_job_name: str,
        role_arn: str,
        bucket_name: str,
        base_job_name: str,
        instance_type: str = 'ml.p3.2xlarge',
        max_jobs: int = 20,
        max_parallel_jobs: int = 4
    ) -> bool:
        """
        Create SageMaker Hyperparameter Tuning job
        
        Args:
            tuning_job_name: Unique name for the tuning job
            role_arn: IAM role ARN for SageMaker
            bucket_name: S3 bucket name
            base_job_name: Base name for training jobs
            instance_type: EC2 instance type
            max_jobs: Maximum number of tuning jobs
            max_parallel_jobs: Maximum parallel jobs
            
        Returns:
            True if job created successfully
        """
        try:
            # PyTorch container image
            image_uri = f'763104351884.dkr.ecr.{self.region}.amazonaws.com/pytorch-training:2.0.0-gpu-py310'
            
            response = self.sagemaker_client.create_hyper_parameter_tuning_job(
                HyperParameterTuningJobName=tuning_job_name,
                HyperParameterTuningJobConfig={
                    'Strategy': 'Bayesian',
                    'HyperParameterTuningJobObjective': {
                        'Type': 'Minimize',
                        'MetricName': 'val:rmse'
                    },
                    'ResourceLimits': {
                        'MaxNumberOfTrainingJobs': max_jobs,
                        'MaxParallelTrainingJobs': max_parallel_jobs
                    },
                    'ParameterRanges': {
                        'ContinuousParameterRanges': [
                            {
                                'Name': 'learning_rate',
                                'MinValue': '0.0001',
                                'MaxValue': '0.01',
                                'ScalingType': 'Logarithmic'
                            }
                        ],
                        'IntegerParameterRanges': [
                            {
                                'Name': 'embedding_dim',
                                'MinValue': '64',
                                'MaxValue': '256',
                                'ScalingType': 'Linear'
                            },
                            {
                                'Name': 'batch_size',
                                'MinValue': '128',
                                'MaxValue': '512',
                                'ScalingType': 'Linear'
                            }
                        ]
                    },
                    'TrainingJobEarlyStoppingType': 'Auto'
                },
                TrainingJobDefinition={
                    'StaticHyperParameters': {
                        'epochs': '50',
                        'num_factors': '50'
                    },
                    'AlgorithmSpecification': {
                        'TrainingImage': image_uri,
                        'TrainingInputMode': 'File',
                        'MetricDefinitions': [
                            {
                                'Name': 'train:rmse',
                                'Regex': 'Train RMSE: ([0-9\\.]+)'
                            },
                            {
                                'Name': 'val:rmse',
                                'Regex': 'Val RMSE: ([0-9\\.]+)'
                            }
                        ]
                    },
                    'RoleArn': role_arn,
                    'InputDataConfig': [
                        {
                            'ChannelName': 'train',
                            'DataSource': {
                                'S3DataSource': {
                                    'S3DataType': 'S3Prefix',
                                    'S3Uri': f's3://{bucket_name}/processed-data/train.csv',
                                    'S3DataDistributionType': 'FullyReplicated'
                                }
                            },
                            'ContentType': 'text/csv'
                        },
                        {
                            'ChannelName': 'validation',
                            'DataSource': {
                                'S3DataSource': {
                                    'S3DataType': 'S3Prefix',
                                    'S3Uri': f's3://{bucket_name}/processed-data/validation.csv',
                                    'S3DataDistributionType': 'FullyReplicated'
                                }
                            },
                            'ContentType': 'text/csv'
                        }
                    ],
                    'OutputDataConfig': {
                        'S3OutputPath': f's3://{bucket_name}/models/'
                    },
                    'ResourceConfig': {
                        'InstanceType': instance_type,
                        'InstanceCount': 1,
                        'VolumeSizeInGB': 50
                    },
                    'StoppingCondition': {
                        'MaxRuntimeInSeconds': 86400
                    }
                }
            )
            
            print(f"✓ Created hyperparameter tuning job: {tuning_job_name}")
            return True
        except ClientError as e:
            print(f"✗ Error creating tuning job: {e}")
            return False
    
    def create_endpoint_config(
        self,
        config_name: str,
        model_name: str,
        instance_type: str = 'ml.m5.xlarge',
        initial_instance_count: int = 2
    ) -> bool:
        """
        Create SageMaker endpoint configuration
        
        Args:
            config_name: Name for the endpoint config
            model_name: Name of the model to deploy
            instance_type: EC2 instance type
            initial_instance_count: Initial number of instances
            
        Returns:
            True if config created successfully
        """
        try:
            response = self.sagemaker_client.create_endpoint_config(
                EndpointConfigName=config_name,
                ProductionVariants=[
                    {
                        'VariantName': 'AllTraffic',
                        'ModelName': model_name,
                        'InitialInstanceCount': initial_instance_count,
                        'InstanceType': instance_type,
                        'InitialVariantWeight': 1.0
                    }
                ],
                DataCaptureConfig={
                    'EnableCapture': True,
                    'InitialSamplingPercentage': 100,
                    'DestinationS3Uri': f's3://{self.bucket_name}/monitoring/data-capture/',
                    'CaptureOptions': [
                        {'CaptureMode': 'Input'},
                        {'CaptureMode': 'Output'}
                    ]
                }
            )
            
            print(f"✓ Created endpoint config: {config_name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException' and 'already exists' in str(e):
                print(f"✓ Endpoint config already exists: {config_name}")
                return True
            print(f"✗ Error creating endpoint config: {e}")
            return False
    
    def deploy_endpoint(
        self,
        endpoint_name: str,
        config_name: str,
        wait: bool = False
    ) -> bool:
        """
        Deploy SageMaker endpoint
        
        Args:
            endpoint_name: Name for the endpoint
            config_name: Name of the endpoint config
            wait: Whether to wait for endpoint to be in service
            
        Returns:
            True if endpoint deployed successfully
        """
        try:
            # Check if endpoint exists
            try:
                self.sagemaker_client.describe_endpoint(EndpointName=endpoint_name)
                # Endpoint exists, update it
                response = self.sagemaker_client.update_endpoint(
                    EndpointName=endpoint_name,
                    EndpointConfigName=config_name
                )
                print(f"✓ Updated endpoint: {endpoint_name}")
            except ClientError as e:
                if e.response['Error']['Code'] == 'ValidationException':
                    # Endpoint doesn't exist, create it
                    response = self.sagemaker_client.create_endpoint(
                        EndpointName=endpoint_name,
                        EndpointConfigName=config_name
                    )
                    print(f"✓ Created endpoint: {endpoint_name}")
                else:
                    raise
            
            if wait:
                print(f"Waiting for endpoint to be in service...")
                waiter = self.sagemaker_client.get_waiter('endpoint_in_service')
                waiter.wait(EndpointName=endpoint_name)
                print(f"✓ Endpoint is in service: {endpoint_name}")
            
            return True
        except ClientError as e:
            print(f"✗ Error deploying endpoint: {e}")
            return False
    
    def create_model(
        self,
        model_name: str,
        role_arn: str,
        model_data_url: str,
        bucket_name: str
    ) -> bool:
        """
        Create SageMaker model from training artifacts
        
        Args:
            model_name: Name for the model
            role_arn: IAM role ARN
            model_data_url: S3 URL to model.tar.gz
            bucket_name: S3 bucket name
            
        Returns:
            True if model created successfully
        """
        try:
            # PyTorch inference container
            image_uri = f'763104351884.dkr.ecr.{self.region}.amazonaws.com/pytorch-inference:2.0.0-gpu-py310'
            
            self.bucket_name = bucket_name  # Store for endpoint config
            
            response = self.sagemaker_client.create_model(
                ModelName=model_name,
                PrimaryContainer={
                    'Image': image_uri,
                    'ModelDataUrl': model_data_url,
                    'Environment': {
                        'SAGEMAKER_PROGRAM': 'inference.py',
                        'SAGEMAKER_SUBMIT_DIRECTORY': model_data_url
                    }
                },
                ExecutionRoleArn=role_arn
            )
            
            print(f"✓ Created model: {model_name}")
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException' and 'already exists' in str(e):
                print(f"✓ Model already exists: {model_name}")
                return True
            print(f"✗ Error creating model: {e}")
            return False


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy SageMaker components for MovieLens recommendation system')
    parser.add_argument('--action', required=True, choices=['processing', 'training', 'tuning', 'endpoint', 'all'],
                       help='Deployment action to perform')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--role-arn', required=True, help='SageMaker execution role ARN')
    parser.add_argument('--bucket-name', required=True, help='S3 bucket name')
    parser.add_argument('--job-name', help='Job name (for processing/training/tuning)')
    parser.add_argument('--model-name', help='Model name (for endpoint deployment)')
    parser.add_argument('--model-data-url', help='S3 URL to model artifacts')
    parser.add_argument('--endpoint-name', help='Endpoint name')
    
    args = parser.parse_args()
    
    deployment = SageMakerDeployment(args.region)
    
    success = False
    
    if args.action == 'processing':
        job_name = args.job_name or f'movielens-processing-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
        success = deployment.create_processing_job(job_name, args.role_arn, args.bucket_name)
    
    elif args.action == 'training':
        job_name = args.job_name or f'movielens-training-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
        hyperparameters = {
            'epochs': '50',
            'batch_size': '256',
            'learning_rate': '0.001',
            'embedding_dim': '128',
            'num_factors': '50'
        }
        success = deployment.create_training_job(job_name, args.role_arn, args.bucket_name, hyperparameters)
    
    elif args.action == 'tuning':
        job_name = args.job_name or f'movielens-tuning-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
        base_job_name = f'movielens-training'
        success = deployment.create_hyperparameter_tuning_job(
            job_name, args.role_arn, args.bucket_name, base_job_name
        )
    
    elif args.action == 'endpoint':
        if not args.model_name or not args.model_data_url or not args.endpoint_name:
            print("✗ Error: --model-name, --model-data-url, and --endpoint-name required for endpoint deployment")
            exit(1)
        
        # Create model
        model_success = deployment.create_model(
            args.model_name, args.role_arn, args.model_data_url, args.bucket_name
        )
        
        # Create endpoint config
        config_name = f'{args.endpoint_name}-config'
        config_success = deployment.create_endpoint_config(config_name, args.model_name)
        
        # Deploy endpoint
        endpoint_success = deployment.deploy_endpoint(args.endpoint_name, config_name, wait=True)
        
        success = model_success and config_success and endpoint_success
    
    exit(0 if success else 1)


if __name__ == '__main__':
    main()
