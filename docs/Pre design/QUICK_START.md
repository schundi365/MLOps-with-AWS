# Quick Start Guide - Deploy in 10 Minutes

This guide will get your MovieLens recommendation system live on AWS as quickly as possible.

---

## Prerequisites (5 minutes)

1. **AWS Account** with billing enabled
2. **AWS CLI** installed and configured:
   ```bash
   aws configure
   ```
3. **Python 3.10+** installed
4. **Git** installed

---

## Option 1: Automated Deployment (Recommended)

### Step 1: Make scripts executable

```bash
chmod +x deploy_live.sh cleanup.sh
```

### Step 2: Run deployment script

```bash
./deploy_live.sh
```

This will automatically:
- ✅ Check prerequisites
- ✅ Download MovieLens dataset
- ✅ Create AWS infrastructure
- ✅ Upload and preprocess data
- ✅ Train model on SageMaker
- ✅ Deploy inference endpoint
- ✅ Setup monitoring and auto-scaling

**Time**: 60-90 minutes (mostly waiting for training)

---

## Option 2: Manual Deployment

### Step 1: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Set environment variables

```bash
export BUCKET_NAME="movielens-ml-$(aws sts get-caller-identity --query Account --output text)"
export AWS_REGION="us-east-1"
```

### Step 3: Deploy infrastructure

```bash
python src/infrastructure/deploy_all.py \
  --bucket-name $BUCKET_NAME \
  --region $AWS_REGION
```

### Step 4: Upload data

```bash
python src/data_upload.py \
  --dataset 100k \
  --bucket $BUCKET_NAME \
  --prefix raw-data/
```

### Step 5: Train and deploy

```bash
# Train model
python src/infrastructure/sagemaker_deployment.py \
  --bucket-name $BUCKET_NAME \
  --training-job-name movielens-training-$(date +%Y%m%d-%H%M%S)

# Deploy endpoint
python src/infrastructure/sagemaker_deployment.py \
  --bucket-name $BUCKET_NAME \
  --endpoint-name movielens-endpoint
```

---

## Verify Deployment

### Test inference

```bash
python src/inference.py \
  --endpoint-name movielens-endpoint \
  --user-id 1 \
  --movie-id 1
```

**Expected output:**
```
Predicted rating: 4.2
Latency: 45ms
```

### Check CloudWatch dashboard

Visit: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:

---

## What You Get

After deployment, you'll have:

1. **Live Inference Endpoint**
   - URL: `movielens-endpoint.sagemaker.us-east-1.amazonaws.com`
   - Latency: < 500ms P99
   - Auto-scaling: 1-5 instances

2. **Automated ML Pipeline**
   - Weekly retraining (Sundays 2 AM UTC)
   - Orchestrated by Step Functions
   - Triggered by EventBridge

3. **Monitoring & Alerts**
   - CloudWatch dashboard
   - Error rate alarms
   - Latency alarms
   - Cost tracking

4. **Data Storage**
   - S3 bucket with versioning
   - Encrypted at rest
   - Lifecycle policies

---

## Cost Estimate

**Monthly Cost**: $150-300 USD

Breakdown:
- SageMaker endpoint (ml.m5.large): $70-150/month
- SageMaker training (weekly): $50-100/month
- S3 storage: $5-10/month
- Lambda + Step Functions: $5-10/month
- CloudWatch: $10-20/month

**Cost Optimization Tips:**
- Use Spot instances for training (-70% cost)
- Reduce endpoint instance size
- Enable auto-scaling with min=1
- Set S3 lifecycle policies

---

## Common Commands

### Check endpoint status
```bash
aws sagemaker describe-endpoint --endpoint-name movielens-endpoint
```

### View logs
```bash
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint --follow
```

### Trigger manual retraining
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:us-east-1:ACCOUNT_ID:stateMachine:MovieLensMLPipeline
```

### Check costs
```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost
```

---

## Cleanup (When Done)

To delete all resources and stop charges:

```bash
./cleanup.sh
```

Or manually:
```bash
# Delete endpoint
aws sagemaker delete-endpoint --endpoint-name movielens-endpoint

# Delete S3 bucket
aws s3 rb s3://$BUCKET_NAME --force

# Delete other resources (see cleanup.sh for full list)
```

---

## Troubleshooting

### Issue: Training job fails
```bash
# Check logs
aws logs tail /aws/sagemaker/TrainingJobs --follow

# Common fix: Verify data in S3
aws s3 ls s3://$BUCKET_NAME/processed-data/ --recursive
```

### Issue: Endpoint not responding
```bash
# Check status
aws sagemaker describe-endpoint --endpoint-name movielens-endpoint

# Wait for InService status (takes 5-10 minutes)
```

### Issue: High costs
```bash
# Check current spend
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '1 day ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost

# Reduce costs:
# 1. Delete endpoint when not in use
# 2. Use smaller instance types
# 3. Enable auto-scaling with min=0
```

---

## Next Steps

1. **Load Testing**: Test with production traffic
   ```bash
   python tests/integration/test_inference_load.py
   ```

2. **API Gateway**: Expose public API (see DEPLOYMENT_GUIDE.md)

3. **CI/CD**: Setup GitHub Actions for automated deployments

4. **Monitoring**: Review CloudWatch dashboard daily

5. **Documentation**: Update with your specific configurations

---

## Support

- **Detailed Guide**: See DEPLOYMENT_GUIDE.md
- **Operations**: See RUNBOOK.md
- **Architecture**: See ARCHITECTURE.md
- **GitHub**: https://github.com/schundi365/MLOps

---

## Success Checklist

- [ ] AWS credentials configured
- [ ] Dependencies installed
- [ ] Infrastructure deployed
- [ ] Data uploaded to S3
- [ ] Model trained
- [ ] Endpoint deployed and InService
- [ ] Inference test successful
- [ ] Monitoring dashboard visible
- [ ] Auto-scaling configured
- [ ] Weekly retraining scheduled

**🎉 Congratulations! Your system is live!**
