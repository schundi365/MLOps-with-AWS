#!/usr/bin/env python3
"""
Fix Issue #17: Missing training entry point.

Problem: Training job fails with "AttributeError: 'NoneType' object has no attribute 'endswith'"
because SageMaker doesn't know which script to run.

Solution: Add 'sagemaker_program' hyperparameter and 'sagemaker_submit_directory' 
to tell SageMaker to run train.py from the tarball.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #17: Missing Training Entry Point")
    print("="*70)
    print()
    
    # Get current state machine definition
    sfn_client = boto3.client('stepfunctions', region_name=region)
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:MovieLensMLPipeline"
    
    print("Getting current state machine definition...")
    response = sfn_client.describe_state_machine(stateMachineArn=state_machine_arn)
    
    # ARNs
    sagemaker_role_arn = f"arn:aws:iam::{account_id}:role/MovieLensSageMakerRole"
    evaluation_lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:movielens-model-evaluation"
    monitoring_lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:movielens-monitoring-setup"
    
    print("Adding training entry point configuration...")
    print("  sagemaker_program: train.py")
    print("  sagemaker_submit_directory: s3://bucket/code/sourcedir.tar.gz")
    print()
    
    # Create updated state machine definition
    definition = {
        "Comment": "MovieLens ML Pipeline - Complete workflow from preprocessing to deployment",
        "StartAt": "DataPreprocessing",
        "States": {
            "DataPreprocessing": {
                "Type": "Task",
                "Resource": "arn:aws:states:::sagemaker:createProcessingJob.sync",
                "Parameters": {
                    "ProcessingJobName.$": "$.preprocessing_job_name",
                    "RoleArn": sagemaker_role_arn,
                    "AppSpecification": {
                        "ImageUri": f"683313688378.dkr.ecr.{region}.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
                        "ContainerEntrypoint": [
                            "python3",
                            "/opt/ml/processing/input/code/preprocessing.py"
                        ]
                    },
                    "ProcessingInputs": [
                        {
                            "InputName": "code",
                            "S3Input": {
                                "S3Uri": f"s3://{bucket_name}/code/preprocessing.py",
                                "LocalPath": "/opt/ml/processing/input/code",
                                "S3DataType": "S3Prefix",
                                "S3InputMode": "File"
                            }
                        },
                        {
                            "InputName": "data",
                            "S3Input": {
                                "S3Uri": f"s3://{bucket_name}/raw-data/",
                                "LocalPath": "/opt/ml/processing/input/data",
                                "S3DataType": "S3Prefix",
                                "S3InputMode": "File"
                            }
                        }
                    ],
                    "ProcessingOutputConfig": {
                        "Outputs": [
                            {
                                "OutputName": "train",
                                "S3Output": {
                                    "S3Uri": f"s3://{bucket_name}/processed-data/",
                                    "LocalPath": "/opt/ml/processing/output/train",
                                    "S3UploadMode": "EndOfJob"
                                }
                            },
                            {
                                "OutputName": "validation",
                                "S3Output": {
                                    "S3Uri": f"s3://{bucket_name}/processed-data/",
                                    "LocalPath": "/opt/ml/processing/output/validation",
                                    "S3UploadMode": "EndOfJob"
                                }
                            },
                            {
                                "OutputName": "test",
                                "S3Output": {
                                    "S3Uri": f"s3://{bucket_name}/processed-data/",
                                    "LocalPath": "/opt/ml/processing/output/test",
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
                    "StoppingCondition": {
                        "MaxRuntimeInSeconds": 3600
                    }
                },
                "ResultPath": "$.preprocessing_result",
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
                        "TrainingImage": f"763104351884.dkr.ecr.{region}.amazonaws.com/pytorch-training:2.0.0-cpu-py310",
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
                        "num_factors": "50",
                        "sagemaker_program": "train.py",  # ADDED: Entry point script
                        "sagemaker_submit_directory": f"s3://{bucket_name}/code/sourcedir.tar.gz"  # ADDED: Code location
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
                        "InstanceType": "ml.m5.xlarge",
                        "InstanceCount": 1,
                        "VolumeSizeInGB": 50
                    },
                    "StoppingCondition": {
                        "MaxRuntimeInSeconds": 7200
                    },
                    "EnableNetworkIsolation": False,
                    "EnableInterContainerTrafficEncryption": False,
                    "EnableManagedSpotTraining": False
                },
                "ResultPath": "$.training_result",
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
                    "training_job_name.$": "$.training_job_name",
                    "bucket_name": bucket_name,
                    "test_data_path": f"s3://{bucket_name}/processed-data/test.csv"
                },
                "ResultPath": "$.evaluation_result",
                "Next": "CheckEvaluationResult",
                "Retry": [
                    {
                        "ErrorEquals": ["States.TaskFailed", "Lambda.ServiceException"],
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
            "CheckEvaluationResult": {
                "Type": "Choice",
                "Choices": [
                    {
                        "Variable": "$.evaluation_result.rmse",
                        "NumericLessThan": 0.9,
                        "Next": "ModelDeployment"
                    }
                ],
                "Default": "EvaluationThresholdNotMet"
            },
            "ModelDeployment": {
                "Type": "Task",
                "Resource": "arn:aws:states:::sagemaker:createEndpoint",
                "Parameters": {
                    "EndpointName": "movielens-endpoint",
                    "EndpointConfigName.$": "$.endpoint_config_name"
                },
                "ResultPath": "$.deployment_result",
                "Next": "MonitoringSetup",
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
            "MonitoringSetup": {
                "Type": "Task",
                "Resource": monitoring_lambda_arn,
                "Parameters": {
                    "endpoint_name": "movielens-endpoint",
                    "bucket_name": bucket_name
                },
                "ResultPath": "$.monitoring_result",
                "Next": "PipelineSucceeded",
                "Retry": [
                    {
                        "ErrorEquals": ["States.TaskFailed", "Lambda.ServiceException"],
                        "IntervalSeconds": 30,
                        "MaxAttempts": 3,
                        "BackoffRate": 2.0
                    }
                ],
                "Catch": [
                    {
                        "ErrorEquals": ["States.ALL"],
                        "Next": "MonitoringSetupFailed"
                    }
                ]
            },
            "PipelineSucceeded": {
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
            "EvaluationThresholdNotMet": {
                "Type": "Fail",
                "Error": "EvaluationThresholdError",
                "Cause": "Model RMSE did not meet threshold of 0.9"
            },
            "DeploymentFailed": {
                "Type": "Fail",
                "Error": "DeploymentError",
                "Cause": "Model deployment failed"
            },
            "MonitoringSetupFailed": {
                "Type": "Fail",
                "Error": "MonitoringSetupError",
                "Cause": "Monitoring setup failed"
            }
        }
    }
    
    # Update state machine
    print("Updating state machine with entry point configuration...")
    sfn_client.update_state_machine(
        stateMachineArn=state_machine_arn,
        definition=json.dumps(definition)
    )
    
    print("[OK] State machine updated successfully")
    print()
    print("="*70)
    print("FIX APPLIED")
    print("="*70)
    print()
    print("Changes made:")
    print("1. Added 'sagemaker_program': 'train.py' to HyperParameters")
    print("2. Added 'sagemaker_submit_directory': 's3://bucket/code/sourcedir.tar.gz'")
    print()
    print("These tell SageMaker:")
    print("  - Which script to run (train.py)")
    print("  - Where to find the code (sourcedir.tar.gz)")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
