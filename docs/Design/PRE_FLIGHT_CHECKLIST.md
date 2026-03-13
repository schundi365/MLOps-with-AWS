# Pre-Flight Checklist - Before Going Live

Complete this checklist before deploying to AWS to ensure a smooth deployment.

---

## ✅ AWS Account Setup

- [ ] **AWS Account Created**
  - Active AWS account with billing enabled
  - Credit card on file
  - Email verified

- [ ] **IAM User Created**
  - IAM user with Administrator access (or specific permissions)
  - Access Key ID generated
  - Secret Access Key saved securely

- [ ] **AWS CLI Installed**
  ```bash
  aws --version
  # Expected: aws-cli/2.x.x or higher
  ```

- [ ] **AWS Credentials Configured**
  ```bash
  aws configure
  # Enter Access Key ID, Secret Access Key, Region (us-east-1), Format (json)
  ```

- [ ] **AWS Credentials Verified**
  ```bash
  aws sts get-caller-identity
  # Should return your Account ID, UserId, and Arn
  ```

---

## ✅ Local Environment Setup

- [ ] **Python 3.10+ Installed**
  ```bash
  python3 --version
  # Expected: Python 3.10.x or higher
  ```

- [ ] **Git Installed**
  ```bash
  git --version
  # Expected: git version 2.x.x or higher
  ```

- [ ] **Virtual Environment Created** (Recommended)
  ```bash
  python3 -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  ```

- [ ] **Dependencies Installed**
  ```bash
  pip install -r requirements.txt
  # Should install boto3, torch, pandas, etc.
  ```

- [ ] **Dependencies Verified**
  ```bash
  python3 -c "import boto3, torch, pandas; print('All dependencies OK')"
  # Expected: All dependencies OK
  ```

---

## ✅ Cost & Budget Setup

- [ ] **Budget Alert Created**
  - Go to: https://console.aws.amazon.com/billing/home#/budgets
  - Create budget: $300/month
  - Set alert at 80% ($240)
  - Add your email for notifications

- [ ] **Cost Explorer Enabled**
  - Go to: https://console.aws.amazon.com/cost-management/home
  - Enable Cost Explorer (free)

- [ ] **Billing Alerts Enabled**
  - Go to: https://console.aws.amazon.com/billing/home#/preferences
  - Enable "Receive Billing Alerts"

- [ ] **Cost Awareness**
  - Understand estimated monthly cost: $150-300
  - Know how to check costs: `aws ce get-cost-and-usage`
  - Know how to cleanup: `./cleanup.sh`

---

## ✅ Security Checklist

- [ ] **No Hardcoded Credentials**
  ```bash
  # Search for credentials in code
  git grep -i "AKIA"
  git grep -i "aws_access_key"
  # Should return no results (except documentation)
  ```

- [ ] **Environment Variables Set**
  ```bash
  export BUCKET_NAME="movielens-ml-$(aws sts get-caller-identity --query Account --output text)"
  export AWS_REGION="us-east-1"
  echo $BUCKET_NAME
  echo $AWS_REGION
  ```

- [ ] **.gitignore Created**
  - File exists: `.gitignore`
  - Excludes: `.aws/`, `*.pem`, `*.key`, `.env`

- [ ] **MFA Enabled** (Recommended)
  - Go to: https://console.aws.amazon.com/iam/home#/security_credentials
  - Enable MFA for root account
  - Enable MFA for IAM user

---

## ✅ Project Files Verified

- [ ] **Core Files Present**
  ```bash
  ls -la src/
  # Should see: train.py, inference.py, preprocessing.py, etc.
  ```

- [ ] **Infrastructure Files Present**
  ```bash
  ls -la src/infrastructure/
  # Should see: deploy_all.py, sagemaker_deployment.py, etc.
  ```

- [ ] **Test Files Present**
  ```bash
  ls -la tests/
  # Should see: unit/, integration/, properties/
  ```

- [ ] **Documentation Present**
  ```bash
  ls -la *.md
  # Should see: README.md, ARCHITECTURE.md, RUNBOOK.md, etc.
  ```

- [ ] **Deployment Scripts Present**
  ```bash
  ls -la *.sh
  # Should see: deploy_live.sh, cleanup.sh
  ```

---

## ✅ Network & Connectivity

- [ ] **Internet Connection**
  ```bash
  ping -c 3 aws.amazon.com
  # Should receive responses
  ```

- [ ] **AWS API Reachable**
  ```bash
  aws s3 ls
  # Should list S3 buckets (or return empty if none exist)
  ```

- [ ] **GitHub Accessible** (if pushing code)
  ```bash
  git remote -v
  # Should show your GitHub repository
  ```

---

## ✅ Data Preparation

- [ ] **Data Directory Created**
  ```bash
  mkdir -p data
  ls -la data/
  ```

- [ ] **Disk Space Available**
  ```bash
  df -h .
  # Should have at least 5GB free
  ```

- [ ] **Download Tools Available**
  ```bash
  which wget || which curl
  # Should return path to wget or curl
  ```

---

## ✅ Testing Environment

- [ ] **Unit Tests Pass**
  ```bash
  pytest tests/unit/ -v
  # All tests should pass
  ```

- [ ] **Python Imports Work**
  ```bash
  python3 -c "from src.model import CollaborativeFilteringModel; print('OK')"
  # Expected: OK
  ```

- [ ] **AWS SDK Works**
  ```bash
  python3 -c "import boto3; s3 = boto3.client('s3'); print('OK')"
  # Expected: OK
  ```

---

## ✅ Deployment Scripts Ready

- [ ] **Scripts Executable**
  ```bash
  chmod +x deploy_live.sh cleanup.sh
  ls -la *.sh
  # Should show -rwxr-xr-x permissions
  ```

- [ ] **Scripts Syntax Valid**
  ```bash
  bash -n deploy_live.sh
  bash -n cleanup.sh
  # Should return no errors
  ```

---

## ✅ Documentation Reviewed

- [ ] **Read QUICK_START.md**
  - Understand deployment steps
  - Know estimated time (60-90 minutes)
  - Familiar with commands

- [ ] **Read GO_LIVE_SUMMARY.md**
  - Understand what you'll get
  - Know the costs
  - Familiar with monitoring

- [ ] **Skimmed DEPLOYMENT_GUIDE.md**
  - Know where to find detailed instructions
  - Familiar with troubleshooting section

- [ ] **Reviewed RUNBOOK.md**
  - Know how to monitor system
  - Familiar with common issues
  - Know escalation procedures

---

## ✅ Backup & Recovery Plan

- [ ] **Code Backed Up**
  ```bash
  git status
  git log --oneline -5
  # Verify code is committed
  ```

- [ ] **GitHub Repository Ready**
  ```bash
  git remote -v
  # Should show GitHub repository URL
  ```

- [ ] **Recovery Plan Understood**
  - Know how to redeploy if needed
  - Know where model artifacts are stored (S3)
  - Know how to restore from backup

---

## ✅ Communication Plan

- [ ] **Email for Alerts Configured**
  - Email address ready for SNS notifications
  - Email can receive AWS alerts

- [ ] **Team Notified** (if applicable)
  - Team knows deployment is happening
  - Team has access to documentation
  - Team knows how to check status

- [ ] **Stakeholders Informed** (if applicable)
  - Stakeholders know system will be live
  - Stakeholders know estimated costs
  - Stakeholders know monitoring plan

---

## ✅ Final Checks

- [ ] **Time Allocated**
  - Have 2-3 hours available
  - Not deploying during critical business hours
  - Can monitor deployment progress

- [ ] **Rollback Plan Ready**
  - Know how to run `./cleanup.sh`
  - Know how to delete specific resources
  - Have backup of current state

- [ ] **Success Criteria Defined**
  - Endpoint is InService
  - Inference test returns predictions
  - CloudWatch dashboard shows metrics
  - Costs are within budget

---

## 🚀 Ready to Deploy?

If you've checked all items above, you're ready to go live!

### Next Steps:

**Option 1: Automated Deployment**
```bash
./deploy_live.sh
```

**Option 2: Manual Deployment**
```bash
# Follow QUICK_START.md or DEPLOYMENT_GUIDE.md
```

---

## 📋 Post-Deployment Checklist

After deployment completes, verify:

- [ ] **Endpoint Status**
  ```bash
  aws sagemaker describe-endpoint --endpoint-name movielens-endpoint
  # Status should be: InService
  ```

- [ ] **Inference Test**
  ```bash
  python src/inference.py --endpoint-name movielens-endpoint --user-id 1 --movie-id 1
  # Should return predicted rating
  ```

- [ ] **CloudWatch Dashboard**
  - Visit: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
  - Dashboard "MovieLensMonitoring" exists
  - Metrics are populating

- [ ] **Auto-Scaling Configured**
  ```bash
  aws application-autoscaling describe-scalable-targets --service-namespace sagemaker
  # Should show movielens-endpoint with min=1, max=5
  ```

- [ ] **Weekly Retraining Scheduled**
  ```bash
  aws events describe-rule --name MovieLensWeeklyRetraining
  # Should show schedule: cron(0 2 ? * SUN *)
  ```

- [ ] **Costs Tracking**
  ```bash
  aws ce get-cost-and-usage \
    --time-period Start=$(date +%Y-%m-%d),End=$(date -d '+1 day' +%Y-%m-%d) \
    --granularity DAILY \
    --metrics BlendedCost
  # Should show current day's costs
  ```

---

## ⚠️ If Something Goes Wrong

1. **Check logs**:
   ```bash
   aws logs tail /aws/sagemaker/TrainingJobs --follow
   ```

2. **Review RUNBOOK.md** for troubleshooting

3. **Run cleanup if needed**:
   ```bash
   ./cleanup.sh
   ```

4. **Try again** after fixing issues

---

## 📞 Support

- **Documentation**: See DEPLOYMENT_GUIDE.md, RUNBOOK.md
- **AWS Support**: https://console.aws.amazon.com/support/
- **GitHub Issues**: https://github.com/schundi365/MLOps/issues

---

**Good luck with your deployment! 🎉**
