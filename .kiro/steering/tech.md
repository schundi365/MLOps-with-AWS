# Technology Stack

## Core Technologies

### Language & Runtime
- **Python 3.10+**: Primary development language
- **PyTorch 2.0+**: Deep learning framework for collaborative filtering model

### AWS Services
- **S3**: Data storage with versioning, encryption, lifecycle policies
- **SageMaker**: Training jobs, hyperparameter tuning, model hosting
- **Lambda**: Model evaluation and monitoring setup functions
- **Step Functions**: ML pipeline orchestration
- **EventBridge**: Scheduled weekly retraining triggers
- **CloudWatch**: Metrics, logs, dashboards, and alarms
- **IAM**: Least-privilege role-based access control

### ML & Data Libraries
- **torch**: Neural network implementation and training
- **pandas**: Data manipulation and preprocessing
- **numpy**: Numerical computations
- **scikit-learn**: Additional ML utilities
- **boto3**: AWS SDK for Python

### Testing
- **pytest**: Unit and integration testing framework
- **hypothesis**: Property-based testing for universal correctness properties

## Common Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure AWS credentials
aws configure
```

### Testing
```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Run property-based tests
pytest tests/properties/ -v

# Run specific test file
pytest tests/unit/test_model.py -v
```

### Infrastructure Deployment
```bash
# Deploy complete infrastructure
python src/infrastructure/deploy_all.py --bucket-name <bucket> --region us-east-1

# Deploy individual components
python src/infrastructure/iam_setup.py --bucket-name <bucket>
python src/infrastructure/s3_setup.py --bucket-name <bucket> --region us-east-1
python src/infrastructure/lambda_deployment.py --bucket-name <bucket>
python src/infrastructure/stepfunctions_deployment.py --state-machine-name MovieLensMLPipeline
python src/infrastructure/eventbridge_deployment.py --rule-name MovieLensWeeklyRetraining
```

### Data Management
```bash
# Upload MovieLens dataset to S3
python src/data_upload.py --dataset 100k --bucket <bucket> --prefix raw-data/
python src/data_upload.py --dataset 25m --bucket <bucket> --prefix raw-data/
```

### Local Training (Development)
```bash
# Train model locally
python src/train.py \
  --embedding-dim 128 \
  --learning-rate 0.001 \
  --batch-size 256 \
  --epochs 50 \
  --train ./data/train \
  --validation ./data/validation
```

## Build System

- **No build step required**: Pure Python project
- **Dependencies**: Managed via `requirements.txt`
- **Configuration**: `pytest.ini` for test configuration

## Development Workflow

1. Make code changes
2. Run unit tests: `pytest tests/unit/`
3. Run property tests: `pytest tests/properties/`
4. Deploy to AWS: `python src/infrastructure/deploy_all.py`
5. Run integration tests: `pytest tests/integration/`
