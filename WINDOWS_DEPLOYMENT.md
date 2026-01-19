# Windows Deployment Guide

Since you're on Windows, use these PowerShell scripts instead of bash scripts.

---

## Prerequisites

### 1. Install AWS CLI

**Download and install:**
- https://awscli.amazonaws.com/AWSCLIV2.msi

**After installation, close and reopen PowerShell**, then verify:
```powershell
aws --version
```

### 2. Configure AWS Credentials

```powershell
aws configure
```

Enter:
- AWS Access Key ID
- AWS Secret Access Key
- Region: `us-east-1`
- Output format: `json`

### 3. Install Python Dependencies

```powershell
pip install -r requirements.txt
```

---

## Deploy to AWS (Automated)

### Option 1: Run PowerShell Script Directly

```powershell
.\deploy_live.ps1
```

### Option 2: If You Get "Execution Policy" Error

If you see an error about execution policy, run this first:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then try again:
```powershell
.\deploy_live.ps1
```

---

## What the Script Does

The `deploy_live.ps1` script will automatically:

1. ✅ Check prerequisites (AWS CLI, Python, credentials)
2. ✅ Download MovieLens dataset
3. ✅ Upload data to S3
4. ✅ Deploy AWS infrastructure
5. ✅ Preprocess data
6. ✅ Train model on SageMaker (30-45 minutes)
7. ✅ Deploy inference endpoint
8. ✅ Configure auto-scaling
9. ✅ Setup monitoring
10. ✅ Test the endpoint

**Total Time**: 60-90 minutes (mostly waiting for training)

---

## Manual Deployment (Step-by-Step)

If you prefer manual control:

### Step 1: Set Environment Variables

```powershell
$env:BUCKET_NAME = "movielens-ml-$(aws sts get-caller-identity --query Account --output text)"
$env:AWS_REGION = "us-east-1"
```

### Step 2: Deploy Infrastructure

```powershell
python src\infrastructure\deploy_all.py `
  --bucket-name $env:BUCKET_NAME `
  --region $env:AWS_REGION
```

### Step 3: Upload Data

```powershell
python src\data_upload.py `
  --dataset 100k `
  --bucket $env:BUCKET_NAME `
  --prefix raw-data/
```

### Step 4: Preprocess Data

```powershell
python src\preprocessing.py `
  --input-bucket $env:BUCKET_NAME `
  --input-prefix raw-data/ml-100k/ `
  --output-bucket $env:BUCKET_NAME `
  --output-prefix processed-data/ `
  --train-ratio 0.8 `
  --val-ratio 0.1
```

### Step 5: Train Model

```powershell
python src\infrastructure\sagemaker_deployment.py `
  --bucket-name $env:BUCKET_NAME `
  --training-job-name "movielens-training-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
```

### Step 6: Deploy Endpoint

```powershell
python src\infrastructure\sagemaker_deployment.py `
  --bucket-name $env:BUCKET_NAME `
  --endpoint-name movielens-endpoint
```

---

## Test Your Deployment

```powershell
python src\inference.py `
  --endpoint-name movielens-endpoint `
  --user-id 1 `
  --movie-id 1
```

Expected output:
```
Predicted rating: 4.2
Latency: 45ms
```

---

## Monitor Your System

### Check Endpoint Status

```powershell
aws sagemaker describe-endpoint --endpoint-name movielens-endpoint
```

### View CloudWatch Dashboard

Open in browser:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
```

### Check Costs

```powershell
aws ce get-cost-and-usage `
  --time-period Start=$(Get-Date -Format 'yyyy-MM-dd'),End=$(Get-Date).AddDays(1).ToString('yyyy-MM-dd') `
  --granularity DAILY `
  --metrics BlendedCost
```

---

## Cleanup (Delete All Resources)

When you're done testing:

```powershell
.\cleanup.ps1
```

This will delete:
- SageMaker endpoints and models
- S3 bucket and all data
- Lambda functions
- Step Functions
- EventBridge rules
- CloudWatch dashboards
- IAM roles
- All other resources

**⚠️ Warning**: This cannot be undone!

---

## Troubleshooting

### Issue 1: "aws: command not found"

**Solution**: Install AWS CLI
- Download: https://awscli.amazonaws.com/AWSCLIV2.msi
- Install and restart PowerShell

### Issue 2: "Execution policy" error

**Solution**: Allow script execution
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue 3: "Python not found"

**Solution**: Install Python 3.10+
- Download: https://www.python.org/downloads/
- During installation, check "Add Python to PATH"

### Issue 4: "Access Denied" from AWS

**Solution**: Check IAM permissions
- Your IAM user needs Administrator access
- Or specific permissions for SageMaker, S3, Lambda, etc.

### Issue 5: Training job fails

**Solution**: Check logs
```powershell
aws logs tail /aws/sagemaker/TrainingJobs --follow
```

---

## Quick Reference

### Check Prerequisites

```powershell
# AWS CLI
aws --version

# Python
python --version

# AWS credentials
aws sts get-caller-identity

# Dependencies
python -c "import boto3, torch, pandas; print('OK')"
```

### Common Commands

```powershell
# List S3 buckets
aws s3 ls

# List SageMaker endpoints
aws sagemaker list-endpoints

# View logs
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint --follow

# Check costs
aws ce get-cost-and-usage `
  --time-period Start=$(Get-Date).AddDays(-7).ToString('yyyy-MM-dd'),End=$(Get-Date).ToString('yyyy-MM-dd') `
  --granularity DAILY `
  --metrics BlendedCost
```

---

## Files You Need

- ✅ `deploy_live.ps1` - Automated deployment script
- ✅ `cleanup.ps1` - Resource cleanup script
- ✅ `requirements.txt` - Python dependencies
- ✅ All files in `src/` directory

---

## Next Steps

1. **Install AWS CLI** (if not already installed)
2. **Configure credentials**: `aws configure`
3. **Install dependencies**: `pip install -r requirements.txt`
4. **Run deployment**: `.\deploy_live.ps1`
5. **Monitor**: Check CloudWatch dashboard
6. **Test**: Run inference tests
7. **Cleanup**: `.\cleanup.ps1` when done

---

## Cost Estimate

**Monthly**: $150-300 USD
- SageMaker endpoint: $70-150
- Training (weekly): $50-100
- S3 + Lambda + CloudWatch: $30-50

**To minimize costs:**
- Delete endpoint when not in use
- Use Spot instances for training
- Enable auto-scaling with min=1

---

## Support

- **Documentation**: See DEPLOYMENT_GUIDE.md, RUNBOOK.md
- **AWS Console**: https://console.aws.amazon.com/
- **GitHub**: https://github.com/schundi365/MLOps

---

**Ready to deploy? Run: `.\deploy_live.ps1`**
