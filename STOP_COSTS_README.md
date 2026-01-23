# Stop Costs - Quick Reference

## 🚨 Emergency Stop (Fastest Way)

```bash
# Windows PowerShell
.\stop_costs.ps1

# Linux/Mac
./stop_costs.sh
```

This will stop ALL costly resources immediately.

## 🔍 Safe Check First (Recommended)

```bash
# Windows PowerShell
.\stop_costs.ps1 -DryRun

# Linux/Mac
./stop_costs.sh --dry-run
```

This shows what would be stopped WITHOUT actually stopping anything.

## 💰 Expected Savings

**$537 - $1,619 per month**

Breakdown:
- SageMaker Endpoints: $387-969/month (HIGHEST)
- EC2 Instances: $50-200/month
- RDS Databases: $100-300/month
- Training Jobs: $0-50/month
- Notebooks: $0-100/month

## 📋 What Gets Stopped

✅ **Stopped/Deleted:**
- SageMaker Endpoints (deleted)
- SageMaker Training Jobs (stopped)
- SageMaker Notebooks (stopped)
- EC2 Instances (stopped)
- RDS Databases (stopped)
- EventBridge Rules (disabled)

❌ **NOT Touched (Data Safe):**
- S3 Buckets (all data preserved)
- Lambda Functions
- Step Functions
- IAM Roles
- CloudWatch Logs

## 🔄 How to Restart

```bash
# Redeploy everything
python src/infrastructure/deploy_all.py --bucket-name <your-bucket>

# Start the pipeline
python start_pipeline.py
```

## 📚 Full Documentation

See `STOP_COSTS_GUIDE.md` for complete details.

## ⚠️ Important Notes

1. **SageMaker Endpoints are DELETED** (not paused) - must redeploy
2. **Your data in S3 is safe** - never deleted
3. **Always test with --dry-run first**
4. **Costs drop within 1-2 hours** after stopping

## 🆘 Need Help?

1. Check `STOP_COSTS_GUIDE.md` for detailed instructions
2. Check `AWS_COST_ANALYSIS.md` for cost breakdown
3. Run with `--dry-run` to see what would happen
