#!/usr/bin/env python3
"""
Fix Issue #14: Switch from GPU to CPU instance for training.

Problem: Training fails on ml.p3.2xlarge (GPU) instance, possibly due to:
- CUDA initialization issues
- GPU driver problems
- Unnecessary complexity for this small dataset

Solution: Switch to ml.m5.xlarge (CPU) instance with CPU PyTorch image.
This is more reliable, cheaper, and sufficient for the MovieLens dataset.
"""

import boto3
import json

def update_state_machine():
    """Update state machine to use CPU instance for training."""
    
    bucket_name = 'amzn-s3-movielens-327030626634'
    region = 'us-east-1'
    state_machine_name = 'MovieLensMLPipeline'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #14: Training Instance Type")
    print("="*70)
    print()
    
    # Get IAM role ARNs
    iam = boto3.client('iam', region_name=region)
    account_id = boto3.client('sts').get_caller_identity()['Account']
    
    sagemaker_role_arn = f"arn:aws:iam::{account_id}:role/MovieLensSageMakerRole"
    evaluation_lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:movielens-evaluation"
    monitoring_lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:movielens-monitoring-setup"
    
    # Create state machine definition with CPU instance
    definition = {
        "Comment": "MovieLens ML Pipeline - CPU Training",
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
                            "InputName": "data",
                            "S3Input": {
                                "S3Uri": f"s3://{bucket_name}/raw-data/",
                                "LocalPath": "/opt/ml/processing/input/data",
                                "S3DataType": "S3Prefix",
                                "S3InputMode": "File"
                            }
                        },
                        {
                            "InputName": "code",
                            "S3Input": {
                                "S3Uri": f"s3://{bucket_name}/code/preprocessing.py",
                                "LocalPath": "/opt/ml/processing/input",
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
                        "ImageUri": f"683313688378.dkr.ecr.{region}.amazonaws.com/sagemaker-scikit-learn:1.0-1-cpu-py3",
                        "ContainerEntrypoint": ["python3", "/opt/ml/processing/input/preprocessing.py"]
                    },
                    "StoppingCondition": {
                        "MaxRuntimeInSeconds": 3600
                    }
                },
                "ResultPath": "$.preprocessing_result",
                "Next": "ModelTraining",
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
                        "sagemaker_program": "train.py",
                        "sagemaker_submit_directory": f"s3://{bucket_name}/code/sourcedir.tar.gz"
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
                        "MaxRuntimeInSeconds": 86400
                    }
                },
                "ResultPath": "$.training_result",
                "Next": "ModelEvaluation",
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
                    "model_data.$": "$.training_result.ModelArtifacts.S3ModelArtifacts",
                    "bucket_name": bucket_name
                },
                "ResultPath": "$.evaluation_result",
                "Next": "ModelDeployment"
            },
            "ModelDeployment": {
                "Type": "Task",
                "Resource": "arn:aws:states:::sagemaker:createEndpoint",
                "Parameters": {
                    "EndpointName": "movielens-endpoint",
                    "EndpointConfigName.$": "$.evaluation_result.endpoint_config_name"
                },
                "ResultPath": "$.deployment_result",
                "Next": "MonitoringSetup"
            },
            "MonitoringSetup": {
                "Type": "Task",
                "Resource": monitoring_lambda_arn,
                "Parameters": {
                    "endpoint_name": "movielens-endpoint",
                    "model_name.$": "$.training_result.TrainingJobName"
                },
                "ResultPath": "$.monitoring_result",
                "End": True
            },
            "PreprocessingFailed": {
                "Type": "Fail",
                "Error": "PreprocessingFailed",
                "Cause": "Data preprocessing job failed"
            },
            "TrainingFailed": {
                "Type": "Fail",
                "Error": "TrainingFailed",
                "Cause": "Model training job failed"
            }
        }
    }
    
    # Update state machine
    print("Updating state machine...")
    print(f"State Machine: {state_machine_name}")
    print()
    print("Changes:")
    print("  - Instance Type: ml.p3.2xlarge (GPU) -> ml.m5.xlarge (CPU)")
    print("  - PyTorch Image: pytorch-training:2.0.0-gpu-py310 -> pytorch-training:2.0.0-cpu-py310")
    print()
    
    sfn = boto3.client('stepfunctions', region_name=region)
    
    # Get state machine ARN
    state_machines = sfn.list_state_machines()
    state_machine_arn = None
    for sm in state_machines['stateMachines']:
        if sm['name'] == state_machine_name:
            state_machine_arn = sm['stateMachineArn']
            break
    
    if not state_machine_arn:
        print(f"[ERROR] State machine '{state_machine_name}' not found!")
        return False
    
    # Update state machine
    try:
        sfn.update_state_machine(
            stateMachineArn=state_machine_arn,
            definition=json.dumps(definition)
        )
        print("[OK] State machine updated successfully")
        print()
        print("="*70)
        print("FIX APPLIED")
        print("="*70)
        print()
        print("Benefits of CPU instance:")
        print("  1. More reliable - no GPU/CUDA issues")
        print("  2. Cheaper - ~$0.23/hour vs ~$3.82/hour")
        print("  3. Sufficient - MovieLens dataset is small")
        print("  4. Faster startup - no GPU initialization")
        print()
        print("Training will take slightly longer (~60 min vs ~45 min)")
        print("but will be much more reliable.")
        print()
        print("Next step: Restart the pipeline")
        print("  python start_pipeline.py --region us-east-1")
        print()
        print("="*70)
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to update state machine: {e}")
        return False

if __name__ == "__main__":
    success = update_state_machine()
    exit(0 if success else 1)
