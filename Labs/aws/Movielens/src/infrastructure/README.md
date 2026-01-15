# Infrastructure Deployment Scripts

This directory contains infrastructure-as-code deployment scripts for the MovieLens Recommendation System on AWS.

## Overview

The deployment scripts automate the setup of all AWS infrastructure components:

1. **S3 Bucket** - Data storage with versioning, encryption, and lifecycle policies
2. **IAM Roles** - Least-privilege roles for SageMaker, Lambda, and Step Functions
3. **Lambda Functions** - Model evaluation and monitoring setup
4. **Step Functions** - ML pipeline orchestration
5. **EventBridge** - Scheduled weekly retraining

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.10+
- boto3 installed (`pip install boto3`)
- Appropriate AWS permissions to create IAM roles, S3 buckets, Lambda functions, etc.

## Quick Start

Deploy the complete infrastructure with a single command:

```bash
python deploy_all.py --bucket-name movielens-ml-bucket --region us-east-1
```

This will:
1. Create all IAM roles with least-privilege policies
2. Create and configure the S3 bucket
3. Deploy Lambda functions for evaluation and monitoring
4. Deploy the Step Functions state machine
5. Set up EventBridge for weekly retraining (Sundays at 2 AM UTC)

## Individual Component Deployment

You can also deploy components individually:

### 1. S3 Bucket Setup

```bash
python s3_setup.py \
  --bucket-name movielens-ml-bucket \
  --region us-east-1 \
  --sagemaker-role-arn arn:aws:iam::ACCOUNT:role/MovieLensSageMakerRole \
  --lambda-role-arns arn:aws:iam::ACCOUNT:role/MovieLensLambdaEvaluationRole \
                     arn:aws:iam::ACCOUNT:role/MovieLensLambdaMonitoringRole
```

Features:
- Versioning enabled for data lineage
- Server-side encryption (SSE-S3 or SSE-KMS)
- Lifecycle policy to archive to Glacier after 90 days
- Bucket policies for least-privilege access
- Organized directory structure

### 2. IAM Roles and Policies

```bash
python iam_setup.py \
  --bucket-name movielens-ml-bucket
```

Creates:
- **SageMaker Execution Role** - For training and processing jobs
- **Lambda Evaluation Role** - For model evaluation function
- **Lambda Monitoring Role** - For monitoring setup function
- **Step Functions Role** - For pipeline orchestration

All roles follow least-privilege principles with minimal required permissions.

### 3. SageMaker Components

```bash
# Deploy processing job
python sagemaker_deployment.py \
  --action processing \
  --role-arn arn:aws:iam::ACCOUNT:role/MovieLensSageMakerRole \
  --bucket-name movielens-ml-bucket

# Deploy training job
python sagemaker_deployment.py \
  --action training \
  --role-arn arn:aws:iam::ACCOUNT:role/MovieLensSageMakerRole \
  --bucket-name movielens-ml-bucket

# Deploy hyperparameter tuning job
python sagemaker_deployment.py \
  --action tuning \
  --role-arn arn:aws:iam::ACCOUNT:role/MovieLensSageMakerRole \
  --bucket-name movielens-ml-bucket

# Deploy endpoint
python sagemaker_deployment.py \
  --action endpoint \
  --role-arn arn:aws:iam::ACCOUNT:role/MovieLensSageMakerRole \
  --bucket-name movielens-ml-bucket \
  --model-name movielens-model \
  --model-data-url s3://bucket/models/model.tar.gz \
  --endpoint-name movielens-endpoint
```

### 4. Lambda Functions

```bash
python lambda_deployment.py \
  --bucket-name movielens-ml-bucket \
  --evaluation-role-arn arn:aws:iam::ACCOUNT:role/MovieLensLambdaEvaluationRole \
  --monitoring-role-arn arn:aws:iam::ACCOUNT:role/MovieLensLambdaMonitoringRole
```

Deploys:
- **movielens-model-evaluation** - Evaluates trained models on test data
- **movielens-monitoring-setup** - Configures SageMaker Model Monitor

### 5. Step Functions State Machine

```bash
python stepfunctions_deployment.py \
  --state-machine-name MovieLensMLPipeline \
  --role-arn arn:aws:iam::ACCOUNT:role/MovieLensStepFunctionsRole \
  --bucket-name movielens-ml-bucket \
  --sagemaker-role-arn arn:aws:iam::ACCOUNT:role/MovieLensSageMakerRole \
  --evaluation-lambda-arn arn:aws:lambda:REGION:ACCOUNT:function:movielens-model-evaluation \
  --monitoring-lambda-arn arn:aws:lambda:REGION:ACCOUNT:function:movielens-monitoring-setup
```

Creates a state machine that orchestrates:
1. Data preprocessing
2. Model training
3. Model evaluation
4. Deployment decision (based on RMSE threshold)
5. Endpoint deployment
6. Monitoring setup

### 6. EventBridge Scheduled Retraining

```bash
python eventbridge_deployment.py \
  --rule-name MovieLensWeeklyRetraining \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --schedule "cron(0 2 ? * SUN *)"
```

Sets up weekly retraining every Sunday at 2 AM UTC.

## Configuration Options

### S3 Encryption

Use SSE-S3 (default):
```bash
python s3_setup.py --bucket-name my-bucket ...
```

Use SSE-KMS with customer-managed key:
```bash
python s3_setup.py --bucket-name my-bucket --kms-key-id <key-id> ...
```

### Lifecycle Policies

Change Glacier archival period:
```bash
python s3_setup.py --bucket-name my-bucket --days-to-glacier 180 ...
```

### Retraining Schedule

Change schedule to daily at midnight:
```bash
python eventbridge_deployment.py \
  --schedule "cron(0 0 * * ? *)" \
  ...
```

## Directory Structure

After deployment, the S3 bucket will have this structure:

```
s3://movielens-ml-bucket/
├── raw-data/              # Original MovieLens CSV files
├── processed-data/        # Preprocessed train/val/test splits
├── models/                # Trained model artifacts
├── outputs/               # Miscellaneous outputs
├── monitoring/            # Model monitoring data
│   ├── data-capture/      # Captured inference requests/responses
│   ├── baseline/          # Baseline for drift detection
│   └── reports/           # Monitoring reports
└── metrics/               # Evaluation metrics
```

## Troubleshooting

### Permission Errors

Ensure your AWS credentials have permissions to:
- Create IAM roles and policies
- Create S3 buckets
- Create Lambda functions
- Create Step Functions state machines
- Create EventBridge rules

### Bucket Already Exists

If the bucket name is taken, choose a different globally unique name.

### Lambda Deployment Fails

Ensure the source files exist:
- `src/lambda_evaluation.py`
- `src/monitoring.py`

### State Machine Creation Fails

Verify all Lambda function ARNs are correct and the functions exist.

## Clean Up

To delete all resources:

```bash
# Delete EventBridge rule
aws events remove-targets --rule MovieLensWeeklyRetraining --ids 1
aws events delete-rule --name MovieLensWeeklyRetraining

# Delete Step Functions state machine
aws stepfunctions delete-state-machine --state-machine-arn <arn>

# Delete Lambda functions
aws lambda delete-function --function-name movielens-model-evaluation
aws lambda delete-function --function-name movielens-monitoring-setup

# Delete S3 bucket (must be empty first)
aws s3 rm s3://movielens-ml-bucket --recursive
aws s3 rb s3://movielens-ml-bucket

# Delete IAM roles
aws iam delete-role --role-name MovieLensSageMakerRole
aws iam delete-role --role-name MovieLensLambdaEvaluationRole
aws iam delete-role --role-name MovieLensLambdaMonitoringRole
aws iam delete-role --role-name MovieLensStepFunctionsRole
aws iam delete-role --role-name MovieLensEventBridgeRole
```

## Next Steps

After infrastructure deployment:

1. **Upload Data**: Upload MovieLens dataset to `s3://bucket/raw-data/`
2. **Upload Scripts**: Upload preprocessing and training scripts
3. **Start Pipeline**: Execute the Step Functions state machine
4. **Monitor**: Watch pipeline execution in AWS console

## Support

For issues or questions, refer to:
- AWS SageMaker documentation
- AWS Step Functions documentation
- AWS Lambda documentation
- Project requirements and design documents
