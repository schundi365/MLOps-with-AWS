# AWS MovieLens Recommendation System - Implementation Plan

## Overview
This document outlines the complete AWS implementation plan for building a scalable movie recommendation system using the MovieLens dataset with collaborative filtering.

---

## Architecture Components

### 1. Data Pipeline

#### 1.1 Data Ingestion
**Objective**: Acquire and load MovieLens dataset into AWS infrastructure

**Steps**:
- Download MovieLens dataset (recommend starting with MovieLens 25M or 100K for testing)
- Create S3 bucket structure:
  ```
  s3://movielens-recommendation-bucket/
  ├── raw-data/
  │   ├── movies.csv
  │   ├── ratings.csv
  │   ├── tags.csv
  │   └── links.csv
  ├── processed-data/
  │   ├── train/
  │   ├── validation/
  │   └── test/
  ├── models/
  └── outputs/
  ```

**AWS Services**:
- **Amazon S3**: Primary data storage
- **AWS Glue** (optional): For automated ETL jobs
- **AWS Lambda**: Trigger preprocessing on new data uploads

**Implementation**:
```python
# Example: Upload data to S3
import boto3

s3_client = boto3.client('s3')
bucket_name = 'movielens-recommendation-bucket'

# Upload raw data
s3_client.upload_file('movies.csv', bucket_name, 'raw-data/movies.csv')
s3_client.upload_file('ratings.csv', bucket_name, 'raw-data/ratings.csv')
```

#### 1.2 Data Preprocessing
**Objective**: Clean, transform, and prepare data for model training

**Preprocessing Tasks**:
- Handle missing values
- Encode user and movie IDs
- Create user-item interaction matrix
- Split data (80% train, 10% validation, 10% test)
- Normalize ratings
- Feature engineering (user demographics, movie genres, temporal features)

**AWS Services**:
- **AWS Glue**: Serverless ETL
- **Amazon SageMaker Processing**: For complex preprocessing with custom scripts
- **AWS Lambda**: For lightweight transformations

**Example Preprocessing Script**:
```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

# Load data
ratings = pd.read_csv('s3://movielens-recommendation-bucket/raw-data/ratings.csv')
movies = pd.read_csv('s3://movielens-recommendation-bucket/raw-data/movies.csv')

# Create user-item matrix
user_item_matrix = ratings.pivot(index='userId', columns='movieId', values='rating')

# Split data
train_data, temp_data = train_test_split(ratings, test_size=0.2, random_state=42)
val_data, test_data = train_test_split(temp_data, test_size=0.5, random_state=42)

# Save to S3
train_data.to_csv('s3://movielens-recommendation-bucket/processed-data/train/train.csv', index=False)
val_data.to_csv('s3://movielens-recommendation-bucket/processed-data/validation/val.csv', index=False)
test_data.to_csv('s3://movielens-recommendation-bucket/processed-data/test/test.csv', index=False)
```

#### 1.3 S3 Storage Strategy
**Bucket Configuration**:
- Enable versioning for data lineage
- Configure lifecycle policies (archive old data to Glacier after 90 days)
- Enable server-side encryption (SSE-S3 or SSE-KMS)
- Set up bucket policies for least-privilege access

---

### 2. Model Training with Amazon SageMaker

#### 2.1 Collaborative Filtering Approach
**Algorithm Options**:

1. **Matrix Factorization (Recommended)**
   - Singular Value Decomposition (SVD)
   - Alternating Least Squares (ALS)
   - Neural Collaborative Filtering (NCF)

2. **SageMaker Built-in Algorithms**:
   - Factorization Machines
   - Object2Vec (for item embeddings)

3. **Custom Algorithm**:
   - Build PyTorch/TensorFlow collaborative filtering model
   - Use SageMaker Script Mode

#### 2.2 Training Job Configuration

**SageMaker Training Setup**:
```python
import sagemaker
from sagemaker.pytorch import PyTorch

# Initialize SageMaker session
sagemaker_session = sagemaker.Session()
role = 'arn:aws:iam::ACCOUNT_ID:role/SageMakerExecutionRole'

# Define estimator
estimator = PyTorch(
    entry_point='train.py',
    source_dir='./scripts',
    role=role,
    instance_type='ml.p3.2xlarge',  # GPU instance for faster training
    instance_count=1,
    framework_version='2.0.0',
    py_version='py310',
    hyperparameters={
        'epochs': 50,
        'batch_size': 256,
        'learning_rate': 0.001,
        'embedding_dim': 128,
        'num_factors': 50
    },
    output_path='s3://movielens-recommendation-bucket/models/',
    metric_definitions=[
        {'Name': 'train:rmse', 'Regex': 'Train RMSE: ([0-9\\.]+)'},
        {'Name': 'val:rmse', 'Regex': 'Val RMSE: ([0-9\\.]+)'}
    ]
)

# Start training
estimator.fit({
    'train': 's3://movielens-recommendation-bucket/processed-data/train/',
    'validation': 's3://movielens-recommendation-bucket/processed-data/validation/'
})
```

**Training Script Example (train.py)**:
```python
import torch
import torch.nn as nn
import torch.optim as optim
import pandas as pd
import argparse
import os

class CollaborativeFilteringModel(nn.Module):
    def __init__(self, num_users, num_movies, embedding_dim):
        super().__init__()
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.movie_embedding = nn.Embedding(num_movies, embedding_dim)
        self.user_bias = nn.Embedding(num_users, 1)
        self.movie_bias = nn.Embedding(num_movies, 1)
        
    def forward(self, user_ids, movie_ids):
        user_emb = self.user_embedding(user_ids)
        movie_emb = self.movie_embedding(movie_ids)
        user_b = self.user_bias(user_ids).squeeze()
        movie_b = self.movie_bias(movie_ids).squeeze()
        
        dot_product = (user_emb * movie_emb).sum(dim=1)
        prediction = dot_product + user_b + movie_b
        return prediction

def train(args):
    # Load data
    train_data = pd.read_csv(os.path.join(args.train_dir, 'train.csv'))
    val_data = pd.read_csv(os.path.join(args.validation_dir, 'val.csv'))
    
    # Model initialization
    model = CollaborativeFilteringModel(
        num_users=train_data['userId'].max() + 1,
        num_movies=train_data['movieId'].max() + 1,
        embedding_dim=args.embedding_dim
    )
    
    # Training loop
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)
    
    for epoch in range(args.epochs):
        # Training code here
        train_loss = train_epoch(model, train_data, criterion, optimizer)
        val_loss = validate(model, val_data, criterion)
        
        print(f'Epoch {epoch}: Train RMSE: {train_loss**0.5:.4f}, Val RMSE: {val_loss**0.5:.4f}')
    
    # Save model
    torch.save(model.state_dict(), os.path.join(args.model_dir, 'model.pth'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--batch_size', type=int, default=256)
    parser.add_argument('--learning_rate', type=float, default=0.001)
    parser.add_argument('--embedding_dim', type=int, default=128)
    parser.add_argument('--train_dir', type=str, default=os.environ['SM_CHANNEL_TRAIN'])
    parser.add_argument('--validation_dir', type=str, default=os.environ['SM_CHANNEL_VALIDATION'])
    parser.add_argument('--model_dir', type=str, default=os.environ['SM_MODEL_DIR'])
    
    args = parser.parse_args()
    train(args)
```

#### 2.3 Hyperparameter Tuning
**Using SageMaker Automatic Model Tuning**:
```python
from sagemaker.tuner import HyperparameterTuner, ContinuousParameter, IntegerParameter

hyperparameter_ranges = {
    'learning_rate': ContinuousParameter(0.0001, 0.01),
    'embedding_dim': IntegerParameter(64, 256),
    'batch_size': IntegerParameter(128, 512)
}

tuner = HyperparameterTuner(
    estimator=estimator,
    objective_metric_name='val:rmse',
    objective_type='Minimize',
    hyperparameter_ranges=hyperparameter_ranges,
    max_jobs=20,
    max_parallel_jobs=4
)

tuner.fit({
    'train': 's3://movielens-recommendation-bucket/processed-data/train/',
    'validation': 's3://movielens-recommendation-bucket/processed-data/validation/'
})
```

---

### 3. Model Hosting - SageMaker Endpoint

#### 3.1 Inference Script
**Create inference.py**:
```python
import torch
import json
import numpy as np
from model import CollaborativeFilteringModel

def model_fn(model_dir):
    """Load the model"""
    model = CollaborativeFilteringModel(num_users=NUM_USERS, num_movies=NUM_MOVIES, embedding_dim=128)
    model.load_state_dict(torch.load(f'{model_dir}/model.pth'))
    model.eval()
    return model

def input_fn(request_body, content_type):
    """Parse input data"""
    if content_type == 'application/json':
        input_data = json.loads(request_body)
        return input_data
    raise ValueError(f'Unsupported content type: {content_type}')

def predict_fn(input_data, model):
    """Make predictions"""
    user_ids = torch.tensor(input_data['user_ids'])
    movie_ids = torch.tensor(input_data['movie_ids'])
    
    with torch.no_grad():
        predictions = model(user_ids, movie_ids)
    
    return predictions.numpy().tolist()

def output_fn(prediction, accept):
    """Format output"""
    if accept == 'application/json':
        return json.dumps({'predictions': prediction})
    raise ValueError(f'Unsupported accept type: {accept}')
```

#### 3.2 Deploy Endpoint
```python
from sagemaker.pytorch import PyTorchModel

# Create model from training job
pytorch_model = PyTorchModel(
    model_data=estimator.model_data,
    role=role,
    entry_point='inference.py',
    framework_version='2.0.0',
    py_version='py310'
)

# Deploy endpoint
predictor = pytorch_model.deploy(
    initial_instance_count=2,
    instance_type='ml.m5.xlarge',
    endpoint_name='movielens-recommendation-endpoint'
)
```

#### 3.3 Auto-scaling Configuration
```python
import boto3

client = boto3.client('application-autoscaling')

# Register scalable target
client.register_scalable_target(
    ServiceNamespace='sagemaker',
    ResourceId=f'endpoint/movielens-recommendation-endpoint/variant/AllTraffic',
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    MinCapacity=1,
    MaxCapacity=5
)

# Define scaling policy
client.put_scaling_policy(
    PolicyName='movielens-scaling-policy',
    ServiceNamespace='sagemaker',
    ResourceId=f'endpoint/movielens-recommendation-endpoint/variant/AllTraffic',
    ScalableDimension='sagemaker:variant:DesiredInstanceCount',
    PolicyType='TargetTrackingScaling',
    TargetTrackingScalingPolicyConfiguration={
        'TargetValue': 70.0,
        'PredefinedMetricSpecification': {
            'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
        },
        'ScaleInCooldown': 300,
        'ScaleOutCooldown': 60
    }
)
```

#### 3.4 Invoke Endpoint
```python
import json

# Make prediction
response = predictor.predict({
    'user_ids': [123, 123, 456],
    'movie_ids': [1, 50, 100]
})

print(f"Predicted ratings: {response}")
```

---

### 4. Monitoring with Amazon CloudWatch

#### 4.1 Endpoint Monitoring
**Key Metrics to Track**:
- Invocations per minute
- Model latency (P50, P90, P99)
- Error rates (4xx, 5xx)
- Instance CPU/Memory utilization
- Model accuracy drift

**CloudWatch Dashboard Setup**:
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# Create dashboard
dashboard_body = {
    "widgets": [
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/SageMaker", "ModelLatency", {"stat": "Average"}],
                    [".", ".", {"stat": "p99"}]
                ],
                "period": 300,
                "stat": "Average",
                "region": "us-east-1",
                "title": "Model Latency"
            }
        },
        {
            "type": "metric",
            "properties": {
                "metrics": [
                    ["AWS/SageMaker", "Invocations"],
                    [".", "InvocationErrors"]
                ],
                "period": 60,
                "stat": "Sum",
                "region": "us-east-1",
                "title": "Endpoint Invocations"
            }
        }
    ]
}

cloudwatch.put_dashboard(
    DashboardName='MovieLens-Recommendation-Dashboard',
    DashboardBody=json.dumps(dashboard_body)
)
```

#### 4.2 CloudWatch Alarms
```python
# Create alarm for high error rate
cloudwatch.put_metric_alarm(
    AlarmName='MovieLens-HighErrorRate',
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2,
    MetricName='ModelInvocationErrors',
    Namespace='AWS/SageMaker',
    Period=300,
    Statistic='Average',
    Threshold=5.0,
    ActionsEnabled=True,
    AlarmActions=['arn:aws:sns:us-east-1:ACCOUNT_ID:alerts'],
    AlarmDescription='Alert when error rate exceeds 5%'
)

# Create alarm for high latency
cloudwatch.put_metric_alarm(
    AlarmName='MovieLens-HighLatency',
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2,
    MetricName='ModelLatency',
    Namespace='AWS/SageMaker',
    Period=300,
    Statistic='Average',
    Threshold=1000.0,  # 1 second
    ActionsEnabled=True,
    AlarmActions=['arn:aws:sns:us-east-1:ACCOUNT_ID:alerts'],
    AlarmDescription='Alert when latency exceeds 1 second'
)
```

#### 4.3 Model Quality Monitoring
**SageMaker Model Monitor Setup**:
```python
from sagemaker.model_monitor import DataCaptureConfig, DefaultModelMonitor

# Enable data capture
data_capture_config = DataCaptureConfig(
    enable_capture=True,
    sampling_percentage=100,
    destination_s3_uri='s3://movielens-recommendation-bucket/monitoring/data-capture'
)

# Deploy with monitoring
predictor = pytorch_model.deploy(
    initial_instance_count=2,
    instance_type='ml.m5.xlarge',
    endpoint_name='movielens-recommendation-endpoint',
    data_capture_config=data_capture_config
)

# Create baseline
my_monitor = DefaultModelMonitor(
    role=role,
    instance_count=1,
    instance_type='ml.m5.xlarge',
    volume_size_in_gb=20,
    max_runtime_in_seconds=3600
)

# Suggest baseline
my_monitor.suggest_baseline(
    baseline_dataset='s3://movielens-recommendation-bucket/processed-data/validation/val.csv',
    dataset_format={'csv': {'header': True}},
    output_s3_uri='s3://movielens-recommendation-bucket/monitoring/baseline'
)

# Create monitoring schedule
my_monitor.create_monitoring_schedule(
    endpoint_input=predictor.endpoint_name,
    output_s3_uri='s3://movielens-recommendation-bucket/monitoring/reports',
    statistics=my_monitor.baseline_statistics(),
    constraints=my_monitor.suggested_constraints(),
    schedule_cron_expression='cron(0 * ? * * *)'  # Hourly
)
```

#### 4.4 Custom Metrics
**Log custom business metrics**:
```python
def log_recommendation_metrics(user_id, recommended_movies, user_interaction):
    """Log custom metrics to CloudWatch"""
    cloudwatch = boto3.client('cloudwatch')
    
    # Calculate click-through rate
    ctr = user_interaction / len(recommended_movies)
    
    cloudwatch.put_metric_data(
        Namespace='MovieLens/Recommendations',
        MetricData=[
            {
                'MetricName': 'ClickThroughRate',
                'Value': ctr,
                'Unit': 'Percent'
            },
            {
                'MetricName': 'RecommendationsServed',
                'Value': len(recommended_movies),
                'Unit': 'Count'
            }
        ]
    )
```

---

### 5. Automation with AWS Step Functions

#### 5.1 ML Pipeline Orchestration
**Step Functions State Machine**:
```json
{
  "Comment": "MovieLens Recommendation System Training Pipeline",
  "StartAt": "DataPreprocessing",
  "States": {
    "DataPreprocessing": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sagemaker:createProcessingJob.sync",
      "Parameters": {
        "ProcessingJobName.$": "$.preprocessing_job_name",
        "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/SageMakerExecutionRole",
        "ProcessingInputs": [
          {
            "InputName": "raw-data",
            "S3Input": {
              "S3Uri": "s3://movielens-recommendation-bucket/raw-data/",
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
                "S3Uri": "s3://movielens-recommendation-bucket/processed-data/",
                "LocalPath": "/opt/ml/processing/output",
                "S3UploadMode": "EndOfJob"
              }
            }
          ]
        },
        "AppSpecification": {
          "ImageUri": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/preprocessing:latest"
        },
        "ProcessingResources": {
          "ClusterConfig": {
            "InstanceCount": 1,
            "InstanceType": "ml.m5.xlarge",
            "VolumeSizeInGB": 30
          }
        }
      },
      "Next": "ModelTraining"
    },
    "ModelTraining": {
      "Type": "Task",
      "Resource": "arn:aws:states:::sagemaker:createTrainingJob.sync",
      "Parameters": {
        "TrainingJobName.$": "$.training_job_name",
        "RoleArn": "arn:aws:iam::ACCOUNT_ID:role/SageMakerExecutionRole",
        "AlgorithmSpecification": {
          "TrainingImage": "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/collaborative-filtering:latest",
          "TrainingInputMode": "File"
        },
        "InputDataConfig": [
          {
            "ChannelName": "train",
            "DataSource": {
              "S3DataSource": {
                "S3DataType": "S3Prefix",
                "S3Uri": "s3://movielens-recommendation-bucket/processed-data/train/",
                "S3DataDistributionType": "FullyReplicated"
              }
            }
          },
          {
            "ChannelName": "validation",
            "DataSource": {
              "S3DataSource": {
                "S3DataType": "S3Prefix",
                "S3Uri": "s3://movielens-recommendation-bucket/processed-data/validation/",
                "S3DataDistributionType": "FullyReplicated"
              }
            }
          }
        ],
        "OutputDataConfig": {
          "S3OutputPath": "s3://movielens-recommendation-bucket/models/"
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
      "Next": "ModelEvaluation"
    },
    "ModelEvaluation": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "movielens-model-evaluation",
        "Payload": {
          "model_data.$": "$.ModelArtifacts.S3ModelArtifacts"
        }
      },
      "Next": "EvaluationCheck"
    },
    "EvaluationCheck": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.Payload.rmse",
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
        "EndpointName": "movielens-recommendation-endpoint",
        "EndpointConfigName.$": "$.endpoint_config_name"
      },
      "Next": "EnableMonitoring"
    },
    "EnableMonitoring": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "enable-model-monitoring",
        "Payload": {
          "endpoint_name": "movielens-recommendation-endpoint"
        }
      },
      "Next": "Success"
    },
    "Success": {
      "Type": "Succeed"
    },
    "ModelTrainingFailed": {
      "Type": "Fail",
      "Error": "ModelEvaluationFailed",
      "Cause": "Model RMSE exceeds threshold"
    }
  }
}
```

#### 5.2 Lambda Functions for Pipeline

**Model Evaluation Function**:
```python
import boto3
import json
import pandas as pd
from sklearn.metrics import mean_squared_error
import numpy as np

def lambda_handler(event, context):
    """Evaluate trained model on test set"""
    s3 = boto3.client('s3')
    sagemaker_runtime = boto3.client('sagemaker-runtime')
    
    # Load test data
    test_data = pd.read_csv('s3://movielens-recommendation-bucket/processed-data/test/test.csv')
    
    # Get predictions
    endpoint_name = 'movielens-recommendation-endpoint-temp'
    predictions = []
    
    for _, row in test_data.iterrows():
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps({
                'user_ids': [int(row['userId'])],
                'movie_ids': [int(row['movieId'])]
            })
        )
        pred = json.loads(response['Body'].read())
        predictions.append(pred['predictions'][0])
    
    # Calculate metrics
    rmse = np.sqrt(mean_squared_error(test_data['rating'], predictions))
    mae = np.mean(np.abs(test_data['rating'] - np.array(predictions)))
    
    # Store metrics
    metrics = {
        'rmse': float(rmse),
        'mae': float(mae),
        'test_samples': len(test_data)
    }
    
    s3.put_object(
        Bucket='movielens-recommendation-bucket',
        Key='metrics/evaluation_results.json',
        Body=json.dumps(metrics)
    )
    
    return metrics
```

**Enable Monitoring Function**:
```python
import boto3

def lambda_handler(event, context):
    """Enable model monitoring for deployed endpoint"""
    sagemaker = boto3.client('sagemaker')
    
    endpoint_name = event['endpoint_name']
    
    # Create monitoring schedule
    sagemaker.create_model_quality_job_definition(
        JobDefinitionName=f'{endpoint_name}-quality-monitoring',
        RoleArn='arn:aws:iam::ACCOUNT_ID:role/SageMakerExecutionRole',
        ModelQualityAppSpecification={
            'ImageUri': 'SAGEMAKER_MODEL_MONITOR_IMAGE',
            'ProblemType': 'Regression'
        },
        ModelQualityJobInput={
            'EndpointInput': {
                'EndpointName': endpoint_name,
                'LocalPath': '/opt/ml/processing/input/endpoint'
            }
        },
        ModelQualityJobOutputConfig={
            'MonitoringOutputs': [{
                'S3Output': {
                    'S3Uri': 's3://movielens-recommendation-bucket/monitoring/quality',
                    'LocalPath': '/opt/ml/processing/output'
                }
            }]
        },
        JobResources={
            'ClusterConfig': {
                'InstanceCount': 1,
                'InstanceType': 'ml.m5.xlarge',
                'VolumeSizeInGB': 20
            }
        }
    )
    
    return {'status': 'Monitoring enabled'}
```

#### 5.3 Scheduled Retraining
**EventBridge Rule for Weekly Retraining**:
```python
import boto3

events = boto3.client('events')
stepfunctions = boto3.client('stepfunctions')

# Create EventBridge rule
events.put_rule(
    Name='weekly-model-retraining',
    ScheduleExpression='cron(0 2 ? * SUN *)',  # Every Sunday at 2 AM UTC
    State='ENABLED',
    Description='Trigger weekly model retraining'
)

# Add Step Functions as target
events.put_targets(
    Rule='weekly-model-retraining',
    Targets=[
        {
            'Id': '1',
            'Arn': 'arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:MovieLensTrainingPipeline',
            'RoleArn': 'arn:aws:iam::ACCOUNT_ID:role/EventBridgeStepFunctionsRole',
            'Input': json.dumps({
                'preprocessing_job_name': f'preprocessing-{datetime.now().strftime("%Y%m%d-%H%M%S")}',
                'training_job_name': f'training-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
            })
        }
    ]
)
```

---

## Implementation Timeline

### Phase 1: Data Pipeline (Week 1-2)
- [ ] Set up S3 bucket structure
- [ ] Download and upload MovieLens dataset
- [ ] Create preprocessing scripts
- [ ] Test data pipeline end-to-end

### Phase 2: Model Development (Week 3-4)
- [ ] Develop collaborative filtering model
- [ ] Create training script for SageMaker
- [ ] Run initial training job
- [ ] Perform hyperparameter tuning
- [ ] Evaluate model performance

### Phase 3: Deployment (Week 5)
- [ ] Create inference script
- [ ] Deploy SageMaker endpoint
- [ ] Configure auto-scaling
- [ ] Test endpoint performance
- [ ] Load testing

### Phase 4: Monitoring (Week 6)
- [ ] Set up CloudWatch dashboards
- [ ] Create CloudWatch alarms
- [ ] Configure Model Monitor
- [ ] Implement custom metrics logging

### Phase 5: Automation (Week 7-8)
- [ ] Build Step Functions state machine
- [ ] Create Lambda functions
- [ ] Set up scheduled retraining
- [ ] End-to-end pipeline testing
- [ ] Documentation and handoff

---

## Cost Estimation

### Monthly Cost Breakdown (Approximate)

**S3 Storage**:
- 10 GB data storage: ~$0.25/month
- Data transfer: ~$5/month

**SageMaker Training**:
- ml.p3.2xlarge (weekly retraining, 2 hours): ~$12/week = $48/month

**SageMaker Hosting**:
- 2 × ml.m5.xlarge (24/7): ~$350/month

**SageMaker Processing**:
- ml.m5.xlarge (weekly, 1 hour): ~$0.23/week = $1/month

**CloudWatch**:
- Logs and metrics: ~$10/month

**Step Functions**:
- State transitions: ~$1/month

**Lambda**:
- Negligible (free tier)

**Total Estimated Cost: ~$415/month**

**Cost Optimization Tips**:
- Use Spot Instances for training (60-70% savings)
- Use SageMaker Serverless Inference for low-traffic scenarios
- Implement S3 Intelligent Tiering
- Use Reserved Instances for production endpoints

---

## Security Best Practices

1. **IAM Roles**: Create least-privilege IAM roles for each service
2. **Encryption**: Enable encryption at rest (S3, SageMaker) and in transit
3. **VPC**: Deploy SageMaker endpoints in private VPC
4. **Secrets Management**: Use AWS Secrets Manager for API keys
5. **Logging**: Enable CloudTrail for audit logging
6. **Access Control**: Implement S3 bucket policies and SageMaker resource policies

---

## Performance Optimization

1. **Training**:
   - Use distributed training for large datasets
   - Implement gradient accumulation
   - Use mixed precision training (FP16)

2. **Inference**:
   - Batch predictions when possible
   - Use model compilation (SageMaker Neo)
   - Implement caching for popular recommendations

3. **Data Pipeline**:
   - Use AWS Glue for parallel processing
   - Implement incremental data updates
   - Use Parquet format for better compression

---

## Monitoring Checklist

- [ ] Endpoint availability (target: 99.9% uptime)
- [ ] Model latency (target: <500ms P99)
- [ ] Error rate (target: <0.1%)
- [ ] Model accuracy (RMSE, MAE)
- [ ] Data drift detection
- [ ] Cost anomaly detection
- [ ] Security alerts

---

## References

- AWS SageMaker Documentation: https://docs.aws.amazon.com/sagemaker/
- MovieLens Dataset: https://grouplens.org/datasets/movielens/
- AWS Step Functions: https://docs.aws.amazon.com/step-functions/
- SageMaker Examples: https://github.com/aws/amazon-sagemaker-examples
