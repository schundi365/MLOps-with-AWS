"""
Step Functions Deployment Script for MovieLens Recommendation System

This script deploys the Step Functions state machine for ML pipeline orchestration:
- State machine definition with all pipeline steps
- IAM permissions configuration
- Error handling and retry logic

Requirements: 9.1
"""

import boto3
import json
from typing import Optional
from botocore.exceptions import ClientError


class StepFunctionsDeployment:
    """Manages Step Functions state machine deployment"""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize Step Functions deployment
        
        Args:
            region: AWS region
        """
        self.region = region
        self.sfn_client = boto3.client('stepfunctions', region_name=region)
        self.account_id = boto3.client('sts').get_caller_identity()['Account']
        
    def create_state_machine_definition(
        self,
        bucket_name: str,
        sagemaker_role_arn: str,
        evaluation_lambda_arn: str,
        monitoring_lambda_arn: str
    ) -> dict:
        """
        Create Step Functions state machine definition
        
        Args:
            bucket_name: S3 bucket name
            sagemaker_role_arn: SageMaker execution role ARN
            evaluation_lambda_arn: Evaluation Lambda function ARN
            monitoring_lambda_arn: Monitoring Lambda function ARN
            
        Returns:
            State machine definition as dictionary
        """
        definition = {
            "Comment": "MovieLens ML Pipeline - Data preprocessing, training, evaluation, and deployment",
            "StartAt": "DataPreprocessing",
            "States": {
                "DataPreprocessing": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sagemaker:createProcessingJob.sync",
                    "Parameters": {
                        "ProcessingJobName.$": "$.preprocessing_job_name",
                        "RoleArn": sagemaker_role_arn,
                        "ProcessingInputs": [
                            {
                                "InputName": "raw-data",
                                "S3Input": {
                                    "S3Uri": f"s3://{bucket_name}/raw-data/",
                                    "LocalPath": "/opt/ml/processing/input",
                                    "S3DataType": "S3Prefix",
                                    "S3InputMode": "File"
                                }
                            }
                        ],
                        "ProcessingOutputConfig": {
                            "Outputs": [
                                {
                                    "OutputName": "processed-data",
                                    "S3Output": {
                                        "S3Uri": f"s3://{bucket_name}/processed-data/",
                                        "LocalPath": "/opt/ml/processing/output",
                                        "S3UploadMode": "EndOfJob"
                                    }
                                }
                            ]
                        },
                        "ProcessingResources": {
                            "ClusterConfig": {
                                "InstanceCount": 1,
                                "InstanceType": "ml.m5.xlarge",
                                "VolumeSizeInGB": 30
                            }
                        },
                        "AppSpecification": {
                            "ImageUri": f"683313688378.dkr.ecr.{self.region}.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3",
                            "ContainerEntrypoint": ["python3", "/opt/ml/processing/input/preprocessing.py"]
                        },
                        "StoppingCondition": {
                            "MaxRuntimeInSeconds": 3600
                        }
                    },
                    "Next": "ModelTraining",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 60,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "PreprocessingFailed"
                        }
                    ]
                },
                "ModelTraining": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sagemaker:createTrainingJob.sync",
                    "Parameters": {
                        "TrainingJobName.$": "$.training_job_name",
                        "RoleArn": sagemaker_role_arn,
                        "AlgorithmSpecification": {
                            "TrainingImage": f"763104351884.dkr.ecr.{self.region}.amazonaws.com/pytorch-training:2.0.0-gpu-py310",
                            "TrainingInputMode": "File",
                            "EnableSageMakerMetricsTimeSeries": True,
                            "MetricDefinitions": [
                                {
                                    "Name": "train:rmse",
                                    "Regex": "Train RMSE: ([0-9\\\\.]+)"
                                },
                                {
                                    "Name": "val:rmse",
                                    "Regex": "Val RMSE: ([0-9\\\\.]+)"
                                }
                            ]
                        },
                        "HyperParameters": {
                            "epochs": "50",
                            "batch_size": "256",
                            "learning_rate": "0.001",
                            "embedding_dim": "128",
                            "num_factors": "50"
                        },
                        "InputDataConfig": [
                            {
                                "ChannelName": "train",
                                "DataSource": {
                                    "S3DataSource": {
                                        "S3DataType": "S3Prefix",
                                        "S3Uri": f"s3://{bucket_name}/processed-data/train.csv",
                                        "S3DataDistributionType": "FullyReplicated"
                                    }
                                },
                                "ContentType": "text/csv"
                            },
                            {
                                "ChannelName": "validation",
                                "DataSource": {
                                    "S3DataSource": {
                                        "S3DataType": "S3Prefix",
                                        "S3Uri": f"s3://{bucket_name}/processed-data/validation.csv",
                                        "S3DataDistributionType": "FullyReplicated"
                                    }
                                },
                                "ContentType": "text/csv"
                            }
                        ],
                        "OutputDataConfig": {
                            "S3OutputPath": f"s3://{bucket_name}/models/"
                        },
                        "ResourceConfig": {
                            "InstanceType": "ml.p3.2xlarge",
                            "InstanceCount": 1,
                            "VolumeSizeInGB": 50
                        },
                        "StoppingCondition": {
                            "MaxRuntimeInSeconds": 86400
                        }
                    },
                    "Next": "ModelEvaluation",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 120,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "TrainingFailed"
                        }
                    ]
                },
                "ModelEvaluation": {
                    "Type": "Task",
                    "Resource": evaluation_lambda_arn,
                    "Parameters": {
                        "model_data.$": "$.ModelArtifacts.S3ModelArtifacts",
                        "bucket_name": bucket_name
                    },
                    "ResultPath": "$.evaluation_results",
                    "Next": "EvaluationCheck",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 30,
                            "MaxAttempts": 3,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "EvaluationFailed"
                        }
                    ]
                },
                "EvaluationCheck": {
                    "Type": "Choice",
                    "Choices": [
                        {
                            "Variable": "$.evaluation_results.rmse",
                            "NumericLessThan": 0.9,
                            "Next": "DeployModel"
                        }
                    ],
                    "Default": "ModelTrainingFailed"
                },
                "DeployModel": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::sagemaker:createEndpoint",
                    "Parameters": {
                        "EndpointName.$": "$.endpoint_name",
                        "EndpointConfigName.$": "$.endpoint_config_name"
                    },
                    "Next": "EnableMonitoring",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 60,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ],
                    "Catch": [
                        {
                            "ErrorEquals": ["States.ALL"],
                            "Next": "DeploymentFailed"
                        }
                    ]
                },
                "EnableMonitoring": {
                    "Type": "Task",
                    "Resource": monitoring_lambda_arn,
                    "Parameters": {
                        "endpoint_name.$": "$.endpoint_name",
                        "bucket_name": bucket_name
                    },
                    "Next": "Success",
                    "Retry": [
                        {
                            "ErrorEquals": ["States.TaskFailed"],
                            "IntervalSeconds": 30,
                            "MaxAttempts": 2,
                            "BackoffRate": 2.0
                        }
                    ]
                },
                "Success": {
                    "Type": "Succeed"
                },
                "PreprocessingFailed": {
                    "Type": "Fail",
                    "Error": "PreprocessingError",
                    "Cause": "Data preprocessing job failed"
                },
                "TrainingFailed": {
                    "Type": "Fail",
                    "Error": "TrainingError",
                    "Cause": "Model training job failed"
                },
                "EvaluationFailed": {
                    "Type": "Fail",
                    "Error": "EvaluationError",
                    "Cause": "Model evaluation failed"
                },
                "ModelTrainingFailed": {
                    "Type": "Fail",
                    "Error": "ModelQualityError",
                    "Cause": "Model RMSE >= 0.9, quality threshold not met"
                },
                "DeploymentFailed": {
                    "Type": "Fail",
                    "Error": "DeploymentError",
                    "Cause": "Model deployment failed"
                }
            }
        }
        
        return definition
    
    def deploy_state_machine(
        self,
        state_machine_name: str,
        role_arn: str,
        definition: dict
    ) -> Optional[str]:
        """
        Deploy Step Functions state machine
        
        Args:
            state_machine_name: Name for the state machine
            role_arn: IAM role ARN for Step Functions execution
            definition: State machine definition
            
        Returns:
            State machine ARN if successful
        """
        try:
            # Check if state machine exists
            try:
                response = self.sfn_client.describe_state_machine(
                    stateMachineArn=f"arn:aws:states:{self.region}:{self.account_id}:stateMachine:{state_machine_name}"
                )
                # State machine exists, update it
                response = self.sfn_client.update_state_machine(
                    stateMachineArn=response['stateMachineArn'],
                    definition=json.dumps(definition),
                    roleArn=role_arn
                )
                print(f"✓ Updated state machine: {state_machine_name}")
                return response['stateMachineArn']
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'StateMachineDoesNotExist':
                    # State machine doesn't exist, create it
                    response = self.sfn_client.create_state_machine(
                        name=state_machine_name,
                        definition=json.dumps(definition),
                        roleArn=role_arn,
                        type='STANDARD'
                    )
                    print(f"✓ Created state machine: {state_machine_name}")
                    return response['stateMachineArn']
                else:
                    raise
                    
        except ClientError as e:
            print(f"✗ Error deploying state machine: {e}")
            return None
    
    def deploy_ml_pipeline(
        self,
        state_machine_name: str,
        role_arn: str,
        bucket_name: str,
        sagemaker_role_arn: str,
        evaluation_lambda_arn: str,
        monitoring_lambda_arn: str
    ) -> Optional[str]:
        """
        Deploy complete ML pipeline state machine
        
        Args:
            state_machine_name: Name for the state machine
            role_arn: Step Functions execution role ARN
            bucket_name: S3 bucket name
            sagemaker_role_arn: SageMaker execution role ARN
            evaluation_lambda_arn: Evaluation Lambda ARN
            monitoring_lambda_arn: Monitoring Lambda ARN
            
        Returns:
            State machine ARN if successful
        """
        print(f"\n=== Deploying Step Functions State Machine ===\n")
        
        # Create state machine definition
        definition = self.create_state_machine_definition(
            bucket_name=bucket_name,
            sagemaker_role_arn=sagemaker_role_arn,
            evaluation_lambda_arn=evaluation_lambda_arn,
            monitoring_lambda_arn=monitoring_lambda_arn
        )
        
        # Deploy state machine
        state_machine_arn = self.deploy_state_machine(
            state_machine_name=state_machine_name,
            role_arn=role_arn,
            definition=definition
        )
        
        if state_machine_arn:
            print(f"\n✓ Successfully deployed ML pipeline state machine")
            print(f"State Machine ARN: {state_machine_arn}")
        
        return state_machine_arn


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy Step Functions state machine for MovieLens recommendation system')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--state-machine-name', default='MovieLensMLPipeline', help='State machine name')
    parser.add_argument('--role-arn', required=True, help='Step Functions execution role ARN')
    parser.add_argument('--bucket-name', required=True, help='S3 bucket name')
    parser.add_argument('--sagemaker-role-arn', required=True, help='SageMaker execution role ARN')
    parser.add_argument('--evaluation-lambda-arn', required=True, help='Evaluation Lambda ARN')
    parser.add_argument('--monitoring-lambda-arn', required=True, help='Monitoring Lambda ARN')
    
    args = parser.parse_args()
    
    deployment = StepFunctionsDeployment(args.region)
    state_machine_arn = deployment.deploy_ml_pipeline(
        state_machine_name=args.state_machine_name,
        role_arn=args.role_arn,
        bucket_name=args.bucket_name,
        sagemaker_role_arn=args.sagemaker_role_arn,
        evaluation_lambda_arn=args.evaluation_lambda_arn,
        monitoring_lambda_arn=args.monitoring_lambda_arn
    )
    
    exit(0 if state_machine_arn else 1)


if __name__ == '__main__':
    main()
