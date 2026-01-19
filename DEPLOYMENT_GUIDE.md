# AWS MovieLens Deployment Guide

## Complete Step-by-Step Guide to Deploy Your Recommendation System Live

This guide will walk you through deploying the MovieLens recommendation system to AWS from scratch.

---

## Prerequisites Checklist

### 1. AWS Account Setup
- [ ] Active AWS account with billing enabled
- [ ] AWS CLI installed and configured
- [ ] IAM user with Administrator access (or specific permissions)
- [ ] AWS credentials configured locally
- [ ] **EventBridge permissions** (for automated retraining) - See Phase 0 below

### 2. Local Environment
- [ ] Python 3.10+ installed
- [ ] Git installed
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)

### 3. Cost Awareness
**Estimated Monthly Cost**: $150-300 USD
- SageMaker training: ~$50-100/month
- SageMaker endpoint: ~$70-150/month (ml.m5.large)
- S3 storage: ~$5-10/month
- Lambda/Step Functions: ~$5-10/month
- CloudWatch: ~$10-20/month

---

## Phase 0: EventBridge Permissions Setup (5 minutes) - OPTIONAL

**Purpose:** Enable automated weekly retraining every Sunday at 2 AM UTC.

**Quick Setup:**
```powershell
python src\infrastructure\add_eventbridge_permissions.py --auto
```

**If you skip this:** Add `--skip-eventbridge` to all deployment commands.

**Detailed instructions:** See [EVENTBRIDGE_SETUP.md](EVENTBRIDGE_SETUP.md)

---

## Phase 1: AWS Account Configuration (15 minutes)

### Step 1.1: Configure AWS CLI

```bash
# Configure AWS credentials
aws configure

# Enter when prompted:
# AWS Access Key ID: [Your Access Key]
# AWS Secret Access Key: [Your Secret Key]
# Default region name: us-east-1
# Default output format: json

# Verify configuration
aws sts get-caller-identity
```

### Step 1.2: Set Environment Variables

```bash
# Set your S3 bucket name (must be globally unique)
export BUCKET_NAME="movielens-ml-$(aws sts get-caller-identity --query Account --output text)"
export AWS_REGION="us-east-1"

# Verify
echo $BUCKET_NAME
echo $AWS_REGION
```

---

## Phase 2: Data Preparation (20 minutes)

### Step 2.1: Download MovieLens Dataset

```bash
# Create local data directory
mkdir -p data

# Download MovieLens 100K dataset (small, for testing)
cd data
wget https://files.grouplens.org/datasets/movielens/ml-100k.zip
unzip ml-100k.zip
cd ..

# OR download MovieLens 25M dataset (production)
# wget https://files.grouplens.org/datasets/movielens/ml-25m.zip
# unzip ml-25m.zip
```

### Step 2.2: Upload Data to S3

```bash
# Upload MovieLens 100K dataset
python src/data_upload.py \
  --dataset 100k \
  --bucket $BUCKET_NAME \
  --prefix raw-data/

# Verify upload
aws s3 ls s3://$BUCKET_NAME/raw-data/ --recursive
```

---

## Phase 3: Infrastructure Deployment (30 minutes)

### Step 3.1: Deploy Complete Infrastructure

```bash
# Deploy all AWS infrastructure components
python src/infrastructure/deploy_all.py \
  --bucket-name $BUCKET_NAME \
  --region $AWS_REGION

# This will create:
# - IAM roles and policies
# - S3 bucket with versioning and encryption
# - Lambda functions for evaluation and monitoring
# - Step Functions state machine
# - EventBridge rule for weekly retraining
# - CloudWatch dashboards and alarms
```

**Expected Output:**
```
✓ IAM roles created
✓ S3 bucket configured
✓ Lambda functions deployed
✓ Step Functions state machine created
✓ EventBridge rule configured
✓ CloudWatch monitoring setup
```

### Step 3.2: Verify Infrastructure

```bash
# Check S3 bucket
aws s3 ls s3://$BUCKET_NAME/

# Check IAM roles
aws iam list-roles | grep MovieLens

# Check Lambda functions
aws lambda list-functions | grep movielens

# Check Step Functions
aws stepfunctions list-state-machines | grep MovieLens
```

---

## Phase 4: Data Preprocessing (15 minutes)

### Step 4.1: Run Preprocessing

```bash
# Preprocess data and create train/val/test splits
python src/preprocessing.py \
  --input-bucket $BUCKET_NAME \
  --input-prefix raw-data/ml-100k/ \
  --output-bucket $BUCKET_NAME \
  --output-prefix processed-data/ \
  --train-ratio 0.8 \
  --val-ratio 0.1

# Verify processed data
aws s3 ls s3://$BUCKET_NAME/processed-data/
```

**Expected Output:**
```
s3://$BUCKET_NAME/processed-data/train/
s3://$BUCKET_NAME/processed-data/validation/
s3://$BUCKET_NAME/processed-data/test/
```

---

## Phase 5: Model Training (45-60 minutes)

### Step 5.1: Local Training (Optional - for testing)

```bash
# Train model locally first to verify everything works
python src/train.py \
  --embedding-dim 128 \
  --learning-rate 0.001 \
  --batch-size 256 \
  --epochs 10 \
  --train ./data/ml-100k/train \
  --validation ./data/ml-100k/validation

# Check output
ls models/
```

### Step 5.2: SageMaker Training Job

```bash
# Deploy SageMaker training job
python src/infrastructure/sagemaker_deployment.py \
  --bucket-name $BUCKET_NAME \
  --role-name MovieLensSageMakerRole \
  --training-job-name movielens-training-$(date +%Y%m%d-%H%M%S)

# Monitor training job
aws sagemaker describe-training-job \
  --training-job-name movielens-training-YYYYMMDD-HHMMSS
```

**Training Time**: 30-45 minutes for 100K dataset

### Step 5.3: Monitor Training Progress

```bash
# Watch CloudWatch logs
aws logs tail /aws/sagemaker/TrainingJobs --follow

# Or check in AWS Console:
# https://console.aws.amazon.com/sagemaker/home?region=us-east-1#/jobs
```

---

## Phase 6: Model Deployment (20 minutes)

### Step 6.1: Create SageMaker Endpoint

```bash
# Deploy model to SageMaker endpoint
python src/infrastructure/sagemaker_deployment.py \
  --bucket-name $BUCKET_NAME \
  --model-name movielens-model \
  --endpoint-name movielens-endpoint \
  --instance-type ml.m5.large \
  --initial-instance-count 1

# Wait for endpoint to be InService (5-10 minutes)
aws sagemaker describe-endpoint \
  --endpoint-name movielens-endpoint
```

### Step 6.2: Configure Auto-Scaling

```bash
# Setup auto-scaling for the endpoint
python src/autoscaling.py \
  --endpoint-name movielens-endpoint \
  --min-capacity 1 \
  --max-capacity 5 \
  --target-invocations 1000

# Verify auto-scaling
aws application-autoscaling describe-scalable-targets \
  --service-namespace sagemaker
```

---

## Phase 7: Testing the Live System (15 minutes)

### Step 7.1: Test Inference Endpoint

```bash
# Test single prediction
python src/inference.py \
  --endpoint-name movielens-endpoint \
  --user-id 123 \
  --movie-id 456

# Expected output:
# Predicted rating: 4.2
```

### Step 7.2: Load Testing

```bash
# Run load test with multiple requests
python tests/integration/test_inference_load.py \
  --endpoint-name movielens-endpoint \
  --num-requests 100 \
  --concurrency 10

# Check latency metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name ModelLatency \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

---

## Phase 8: Monitoring Setup (10 minutes)

### Step 8.1: Configure CloudWatch Dashboard

```bash
# Create CloudWatch dashboard
python src/monitoring.py \
  --endpoint-name movielens-endpoint \
  --dashboard-name MovieLensMonitoring

# View dashboard:
# https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
```

### Step 8.2: Setup Alarms

```bash
# Create CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name movielens-high-error-rate \
  --alarm-description "Alert when error rate exceeds 5%" \
  --metric-name ModelInvocation4XXErrors \
  --namespace AWS/SageMaker \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Setup SNS topic for alerts
aws sns create-topic --name movielens-alerts
aws sns subscribe \
  --topic-arn arn:aws:sns:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):movielens-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com
```

---

## Phase 9: Automated Retraining (5 minutes)

### Step 9.1: Verify EventBridge Rule

```bash
# Check EventBridge rule for weekly retraining
aws events describe-rule --name MovieLensWeeklyRetraining

# Expected: Runs every Sunday at 2 AM UTC
```

### Step 9.2: Manual Trigger (Optional)

```bash
# Manually trigger retraining pipeline
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):stateMachine:MovieLensMLPipeline \
  --input "{\"bucket\":\"$BUCKET_NAME\",\"prefix\":\"raw-data/\"}"

# Monitor execution
aws stepfunctions describe-execution \
  --execution-arn <execution-arn-from-above>
```

---

## Phase 10: Production Readiness Checklist

### Security
- [ ] IAM roles follow least-privilege principle
- [ ] S3 bucket has encryption enabled
- [ ] VPC endpoints configured (optional but recommended)
- [ ] CloudTrail logging enabled
- [ ] Secrets Manager for sensitive data

### Monitoring
- [ ] CloudWatch dashboard created
- [ ] Alarms configured for errors, latency, and costs
- [ ] SNS notifications setup
- [ ] Log retention policies set

### Cost Optimization
- [ ] Auto-scaling configured
- [ ] S3 lifecycle policies set
- [ ] Spot instances considered for training
- [ ] Budget alerts configured

### Backup & Recovery
- [ ] S3 versioning enabled
- [ ] Model artifacts backed up
- [ ] Disaster recovery plan documented

---

## Phase 11: Create Public API (Optional - 30 minutes)

If you want to expose your recommendation system via a public API:

### Step 11.1: Create API Gateway

```bash
# Create REST API
aws apigateway create-rest-api \
  --name MovieLensAPI \
  --description "Movie Recommendation API"

# Create Lambda proxy integration
# (See detailed steps in API_GATEWAY_SETUP.md)
```

### Step 11.2: Add Authentication

```bash
# Create API key
aws apigateway create-api-key \
  --name MovieLensAPIKey \
  --enabled

# Create usage plan
aws apigateway create-usage-plan \
  --name MovieLensUsagePlan \
  --throttle burstLimit=100,rateLimit=50
```

---

## Verification Checklist

After deployment, verify everything is working:

```bash
# 1. Check S3 bucket
aws s3 ls s3://$BUCKET_NAME/ --recursive

# 2. Check SageMaker endpoint status
aws sagemaker describe-endpoint --endpoint-name movielens-endpoint

# 3. Test inference
python src/inference.py --endpoint-name movielens-endpoint --user-id 1 --movie-id 1

# 4. Check CloudWatch metrics
aws cloudwatch list-metrics --namespace AWS/SageMaker

# 5. Verify Step Functions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):stateMachine:MovieLensMLPipeline

# 6. Check Lambda functions
aws lambda list-functions | grep movielens

# 7. Verify EventBridge rule
aws events list-rules | grep MovieLens
```

---

## Troubleshooting Common Issues

### Issue 1: Training Job Fails

```bash
# Check training job logs
aws logs tail /aws/sagemaker/TrainingJobs --follow

# Common fixes:
# - Verify data format in S3
# - Check IAM role permissions
# - Increase instance size if OOM errors
```

### Issue 2: Endpoint Not Responding

```bash
# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name movielens-endpoint

# Check endpoint logs
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint --follow

# Common fixes:
# - Wait for endpoint to be InService
# - Check model artifacts in S3
# - Verify inference code
```

### Issue 3: High Costs

```bash
# Check current costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost

# Cost reduction strategies:
# - Use Spot instances for training
# - Reduce endpoint instance size
# - Enable auto-scaling with lower min capacity
# - Set S3 lifecycle policies
```

---

## Maintenance Tasks

### Daily
- [ ] Check CloudWatch dashboard
- [ ] Review error logs
- [ ] Monitor costs

### Weekly
- [ ] Review model performance metrics
- [ ] Check for data drift
- [ ] Verify automated retraining completed

### Monthly
- [ ] Review and optimize costs
- [ ] Update dependencies
- [ ] Security audit
- [ ] Backup verification

---

## Cleanup (When Done Testing)

To avoid ongoing charges, delete all resources:

```bash
# Delete SageMaker endpoint
aws sagemaker delete-endpoint --endpoint-name movielens-endpoint

# Delete endpoint configuration
aws sagemaker delete-endpoint-config --endpoint-config-name movielens-endpoint-config

# Delete model
aws sagemaker delete-model --model-name movielens-model

# Delete S3 bucket (WARNING: This deletes all data!)
aws s3 rb s3://$BUCKET_NAME --force

# Delete Lambda functions
aws lambda delete-function --function-name movielens-evaluation
aws lambda delete-function --function-name movielens-monitoring-setup

# Delete Step Functions state machine
aws stepfunctions delete-state-machine \
  --state-machine-arn arn:aws:states:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):stateMachine:MovieLensMLPipeline

# Delete EventBridge rule
aws events remove-targets --rule MovieLensWeeklyRetraining --ids "1"
aws events delete-rule --name MovieLensWeeklyRetraining

# Delete IAM roles (be careful!)
aws iam delete-role --role-name MovieLensSageMakerRole
aws iam delete-role --role-name MovieLensLambdaRole
aws iam delete-role --role-name MovieLensStepFunctionsRole
```

---

## Next Steps

1. **Monitor for 24 hours** - Ensure system is stable
2. **Load testing** - Test with production-level traffic
3. **Documentation** - Update with your specific configurations
4. **Team training** - Share RUNBOOK.md with your team
5. **CI/CD setup** - Automate deployments with GitHub Actions

---

## Support Resources

- **AWS Documentation**: https://docs.aws.amazon.com/sagemaker/
- **Project README**: See README.md
- **Architecture**: See ARCHITECTURE.md
- **Operations**: See RUNBOOK.md
- **GitHub Issues**: https://github.com/schundi365/MLOps/issues

---

## Success Criteria

Your system is live when:
- ✅ SageMaker endpoint is InService
- ✅ Inference requests return predictions < 500ms
- ✅ CloudWatch dashboard shows metrics
- ✅ Auto-scaling is configured
- ✅ Weekly retraining is scheduled
- ✅ Monitoring alerts are active

**Congratulations! Your MovieLens recommendation system is now live on AWS! 🎉**
