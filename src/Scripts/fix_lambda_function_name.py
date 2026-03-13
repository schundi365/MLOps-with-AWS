#!/usr/bin/env python3
"""
Fix Issue #16: Lambda function name mismatch.

Problem: State machine references 'movielens-evaluation' but actual function 
is named 'movielens-model-evaluation'.

Solution: Update state machine definition with correct Lambda function name.
"""

import boto3
import json

def main():
    region = 'us-east-1'
    account_id = '327030626634'
    bucket_name = 'amzn-s3-movielens-327030626634'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #16: Lambda Function Name Mismatch")
    print("="*70)
    print()
    
    # Get current state machine definition
    sfn_client = boto3.client('stepfunctions', region_name=region)
    state_machine_arn = f"arn:aws:states:{region}:{account_id}:stateMachine:MovieLensMLPipeline"
    
    print("Getting current state machine definition...")
    response = sfn_client.describe_state_machine(stateMachineArn=state_machine_arn)
    current_definition = json.loads(response['definition'])
    
    # ARNs
    sagemaker_role_arn = f"arn:aws:iam::{account_id}:role/MovieLensSageMakerRole"
    evaluation_lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:movielens-model-evaluation"  # FIXED!
    monitoring_lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:movielens-monitoring-setup"
    
    print(f"[OLD] Evaluation Lambda: movielens-evaluation")
    print(f"[NEW] Evaluation Lambda: movielens-model-evaluation")
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
                "Resource": evaluation_lambda_arn,  # FIXED: Now uses correct name
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
    print("Updating state machine with correct Lambda function name...")
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
    print("1. Updated ModelEvaluation step to use correct Lambda function")
    print("   OLD: movielens-evaluation")
    print("   NEW: movielens-model-evaluation")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)

if __name__ == "__main__":
    main()
