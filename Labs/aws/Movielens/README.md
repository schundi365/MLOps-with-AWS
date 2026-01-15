# AWS MovieLens Recommendation System

A scalable, production-ready movie recommendation system built on AWS infrastructure using collaborative filtering with the MovieLens dataset.

## Overview

This system implements an end-to-end machine learning pipeline for generating personalized movie recommendations using:
- **Collaborative Filtering**: Matrix factorization-based neural network
- **AWS Services**: S3, SageMaker, Lambda, Step Functions, EventBridge, CloudWatch
- **PyTorch**: Deep learning framework for model training
- **Automated Pipeline**: From data ingestion through deployment and monitoring

## Architecture

The system consists of:
- **Data Pipeline**: S3-based storage with preprocessing for train/val/test splits
- **Training Service**: SageMaker training jobs with hyperparameter tuning
- **Inference Endpoints**: Auto-scaling SageMaker endpoints with <500ms P99 latency
- **Orchestration**: Step Functions state machine coordinating the ML workflow
- **Monitoring**: CloudWatch dashboards, Model Monitor for drift detection, SNS alerts
- **Automated Retraining**: Weekly scheduled pipeline execution

## Prerequisites

### AWS Account Setup
1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Installed and configured
   ```bash
   aws --version  # Should be 2.x or higher
   ```
3. **AWS Credentials**: Configured with sufficient permissions
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, region, and output format
   ```

### Required AWS Permissions
Your IAM user/role needs permissions for:
- S3 (create buckets, upload/download objects)
- SageMaker (create training jobs, endpoints, processing jobs)
- Lambda (create and invoke functions)
- Step Functions (create and execute state machines)
- EventBridge (create rules)
- CloudWatch (create dashboards, alarms, log groups)
- IAM (create roles and policies)

### Local Development Environment
- **Python**: 3.10 or higher
- **pip**: Latest version
- **Git**: For cloning the repository

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd aws-movielens-recommendation
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
pytest tests/unit/ -v
```

## Quick Start

### Step 1: Upload MovieLens Dataset

Download and upload the MovieLens dataset to S3:

```bash
# Upload MovieLens 100K dataset (smaller, faster for testing)
python src/data_upload.py \
  --dataset 100k \
  --bucket your-bucket-name \
  --prefix raw-data/

# OR upload MovieLens 25M dataset (larger, production-ready)
python src/data_upload.py \
  --dataset 25m \
  --bucket your-bucket-name \
  --prefix raw-data/
```

This will:
- Download the MovieLens dataset
- Upload CSV files to S3 at `s3://your-bucket-name/raw-data/`
- Verify file integrity

### Step 2: Deploy Infrastructure

Deploy all AWS infrastructure components:

```bash
python src/infrastructure/deploy_all.py \
  --bucket-name your-bucket-name \
  --region us-east-1
```

This creates:
- S3 bucket with proper configuration
- IAM roles and policies
- Lambda functions (evaluation, monitoring)
- Step Functions state machine
- EventBridge scheduled rule
- CloudWatch dashboards and alarms

**Note**: This step may take 5-10 minutes to complete.

### Step 3: Run the ML Pipeline

Trigger the ML pipeline via Step Functions:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --input '{
    "bucket": "your-bucket-name",
    "raw_data_prefix": "raw-data/",
    "processed_data_prefix": "processed-data/",
    "model_prefix": "models/",
    "embedding_dim": 128,
    "learning_rate": 0.001,
    "batch_size": 256,
    "epochs": 50
  }'
```

The pipeline will:
1. Preprocess data (split into train/val/test)
2. Train collaborative filtering model
3. Evaluate model on test set
4. Deploy endpoint (if RMSE < 0.9)
5. Enable monitoring

**Pipeline Duration**: 30-60 minutes depending on dataset size and instance types.

### Step 4: Invoke the Endpoint

Once deployed, make predictions:

```bash
# Get endpoint name
aws sagemaker list-endpoints --query 'Endpoints[?EndpointName.contains(@, `movielens`)].EndpointName' --output text

# Invoke endpoint
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name <endpoint-name> \
  --content-type application/json \
  --body '{"user_ids": [1, 2, 3], "movie_ids": [50, 100, 150]}' \
  output.json

# View predictions
cat output.json
```

Expected output:
```json
{
  "predictions": [4.2, 3.8, 4.5]
}
```

## Detailed Usage

### Running Preprocessing Locally

For development and testing:

```bash
# Preprocess data locally
python src/preprocessing.py \
  --input-dir ./data/raw \
  --output-dir ./data/processed \
  --train-ratio 0.8 \
  --val-ratio 0.1 \
  --test-ratio 0.1
```

This creates:
- `train.csv`: 80% of data
- `validation.csv`: 10% of data
- `test.csv`: 10% of data

### Training Model Locally

Train the model on your local machine:

```bash
python src/train.py \
  --train ./data/processed/train.csv \
  --validation ./data/processed/validation.csv \
  --embedding-dim 128 \
  --learning-rate 0.001 \
  --batch-size 256 \
  --epochs 50 \
  --model-dir ./models
```

Training outputs:
- Model artifacts saved to `./models/model.pth`
- Training logs with RMSE metrics
- Metadata file with hyperparameters

### Deploying the Endpoint

Deploy a trained model to SageMaker:

```bash
python src/infrastructure/sagemaker_deployment.py \
  --model-data s3://your-bucket-name/models/model.tar.gz \
  --endpoint-name movielens-endpoint \
  --instance-type ml.m5.xlarge \
  --instance-count 2
```

Configuration:
- **Instance Type**: `ml.m5.xlarge` (production) or `ml.t2.medium` (development)
- **Instance Count**: 2 for high availability, 1 for development
- **Auto-scaling**: Automatically configured (1-5 instances)

### Invoking the Endpoint

#### Using Python SDK (boto3)

```python
import boto3
import json

client = boto3.client('sagemaker-runtime')

payload = {
    "user_ids": [1, 2, 3],
    "movie_ids": [50, 100, 150]
}

response = client.invoke_endpoint(
    EndpointName='movielens-endpoint',
    ContentType='application/json',
    Body=json.dumps(payload)
)

predictions = json.loads(response['Body'].read())
print(predictions)
```

#### Using AWS CLI

```bash
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name movielens-endpoint \
  --content-type application/json \
  --body '{"user_ids": [1, 2, 3], "movie_ids": [50, 100, 150]}' \
  output.json
```

#### Input Format

```json
{
  "user_ids": [1, 2, 3],      // Array of user IDs
  "movie_ids": [50, 100, 150]  // Array of movie IDs (same length)
}
```

#### Output Format

```json
{
  "predictions": [4.2, 3.8, 4.5]  // Predicted ratings (0-5 scale)
}
```

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit/ -v

# Property-based tests only
pytest tests/properties/ -v

# Integration tests (requires AWS credentials)
pytest tests/integration/ -v
```

### Run Individual Test Files

```bash
pytest tests/unit/test_model.py -v
pytest tests/properties/test_data_pipeline_properties.py -v
```

## Monitoring

### CloudWatch Dashboard

View system metrics:
1. Open AWS Console → CloudWatch → Dashboards
2. Select "MovieLensRecommendationDashboard"
3. View metrics:
   - Invocations per minute
   - Model latency (P50, P90, P99)
   - Error rates (4xx, 5xx)
   - Instance CPU/memory utilization

### CloudWatch Alarms

Configured alarms:
- **High Error Rate**: Triggers when error rate > 5%
- **High Latency**: Triggers when P99 latency > 1000ms

Alarm notifications sent via SNS to configured email/phone.

### Model Monitor

Check for data drift:
1. Open AWS Console → SageMaker → Model Monitor
2. View monitoring schedules and reports
3. Check S3 for detailed reports: `s3://your-bucket-name/monitoring/reports/`

## Scheduled Retraining

The system automatically retrains weekly:
- **Schedule**: Every Sunday at 2 AM UTC
- **Trigger**: EventBridge rule → Step Functions
- **Process**: Complete ML pipeline with latest data

### Manual Retraining

Trigger retraining manually:

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --input '{
    "bucket": "your-bucket-name",
    "raw_data_prefix": "raw-data/",
    "processed_data_prefix": "processed-data/",
    "model_prefix": "models/"
  }'
```

## Configuration

### Hyperparameters

Adjust model hyperparameters in pipeline input:

```json
{
  "embedding_dim": 128,      // Embedding dimension (64-256)
  "learning_rate": 0.001,    // Learning rate (0.0001-0.01)
  "batch_size": 256,         // Batch size (128-512)
  "epochs": 50,              // Training epochs
  "num_factors": 50          // Number of latent factors
}
```

### Auto-scaling

Modify auto-scaling configuration:

```python
# In src/autoscaling.py
config = {
    "min_capacity": 1,
    "max_capacity": 5,
    "target_value": 70,  # Invocations per instance
    "scale_out_cooldown": 60,
    "scale_in_cooldown": 300
}
```

### Monitoring Thresholds

Adjust alarm thresholds:

```python
# In src/monitoring.py
alarms = {
    "error_rate_threshold": 5.0,    # Percentage
    "latency_threshold": 1000.0     # Milliseconds
}
```

## Troubleshooting

### Common Issues

**Issue**: `NoCredentialsError` when running scripts
- **Solution**: Run `aws configure` and enter valid credentials

**Issue**: `AccessDenied` errors
- **Solution**: Verify IAM permissions for your user/role

**Issue**: Training job fails with OOM error
- **Solution**: Reduce `batch_size` or `embedding_dim` hyperparameters

**Issue**: Endpoint returns 400 Bad Request
- **Solution**: Verify input JSON format matches expected schema

**Issue**: High latency on endpoint
- **Solution**: Check auto-scaling configuration and increase max instances

### Logs

View logs in CloudWatch:

```bash
# Training logs
aws logs tail /aws/sagemaker/TrainingJobs --follow

# Endpoint logs
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint --follow

# Lambda logs
aws logs tail /aws/lambda/movielens-evaluation --follow
```

## Cost Optimization

### Development Environment
- Use `ml.t2.medium` instances for endpoints
- Use `ml.m5.large` for training
- Set auto-scaling min to 0 when not in use

### Production Environment
- Use Reserved Instances for endpoints
- Use Spot Instances for training jobs
- Enable S3 Intelligent Tiering
- Set appropriate lifecycle policies

### Estimated Costs (Monthly)
- **Development**: $50-100
- **Production**: $200-500 (depending on traffic)

## Project Structure

```
aws-movielens-recommendation/
├── src/
│   ├── preprocessing.py          # Data preprocessing script
│   ├── model.py                  # Collaborative filtering model
│   ├── train.py                  # Training script
│   ├── inference.py              # Inference script
│   ├── lambda_evaluation.py      # Model evaluation Lambda
│   ├── monitoring.py             # Monitoring setup
│   ├── autoscaling.py            # Auto-scaling configuration
│   ├── retraining.py             # Retraining utilities
│   ├── data_upload.py            # Data upload utility
│   └── infrastructure/           # Infrastructure deployment scripts
│       ├── deploy_all.py
│       ├── s3_setup.py
│       ├── iam_setup.py
│       ├── sagemaker_deployment.py
│       ├── lambda_deployment.py
│       ├── stepfunctions_deployment.py
│       └── eventbridge_deployment.py
├── tests/
│   ├── unit/                     # Unit tests
│   ├── properties/               # Property-based tests
│   └── integration/              # Integration tests
├── requirements.txt              # Python dependencies
├── pytest.ini                    # Pytest configuration
└── README.md                     # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Run test suite: `pytest`
5. Submit pull request

## License

[Your License Here]

## Support

For issues and questions:
- Open an issue on GitHub
- Contact: [Your Contact Info]

## Additional Resources

- [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [MovieLens Dataset](https://grouplens.org/datasets/movielens/)
- [PyTorch Documentation](https://pytorch.org/docs/)
- [Architecture Diagram](ARCHITECTURE.md)
- [Operational Runbook](RUNBOOK.md)
