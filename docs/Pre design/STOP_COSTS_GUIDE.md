# Stop Costs Guide

## Quick Commands

### See what would be stopped (DRY RUN - SAFE)
```bash
# Linux/Mac
./stop_costs.sh --dry-run

# Windows PowerShell
.\stop_costs.ps1 -DryRun

# Python directly
python stop_all_costly_resources.py --region us-east-1 --dry-run
```

### Actually stop resources (DESTRUCTIVE)
```bash
# Linux/Mac
./stop_costs.sh

# Windows PowerShell
.\stop_costs.ps1

# Python directly
python stop_all_costly_resources.py --region us-east-1
```

## What Gets Stopped

### ✅ Resources That Will Be Stopped

1. **SageMaker Endpoints** (DELETED - cannot pause)
   - Cost: ~$387-969/month
   - Impact: Inference API will stop working
   - Recovery: Redeploy using deployment scripts

2. **SageMaker Training Jobs** (STOPPED)
   - Cost: Variable, ~$50/month if running
   - Impact: Any in-progress training will halt
   - Recovery: Restart pipeline

3. **SageMaker Notebook Instances** (STOPPED)
   - Cost: ~$100/month
   - Impact: Notebooks unavailable
   - Recovery: Restart from console or CLI

4. **EC2 Instances** (STOPPED)
   - Cost: ~$50-200/month depending on type
   - Impact: Any EC2-based services stop
   - Recovery: Restart instances

5. **RDS Database Instances** (STOPPED)
   - Cost: ~$100-300/month
   - Impact: Database unavailable
   - Recovery: Restart from console or CLI

6. **EventBridge Rules** (DISABLED)
   - Cost: Minimal
   - Impact: Scheduled retraining won't run
   - Recovery: Re-enable rules

### ❌ Resources NOT Affected (Data Preserved)

- **S3 Buckets**: All data remains intact
- **Lambda Functions**: No cost when idle
- **Step Functions**: No cost when idle
- **IAM Roles**: No cost
- **CloudWatch Logs**: Minimal cost, preserved

## Estimated Savings

| Resource Type | Monthly Savings |
|--------------|----------------|
| SageMaker Endpoints | $387 - $969 |
| EC2 Instances | $50 - $200 |
| RDS Instances | $100 - $300 |
| Training Jobs | $0 - $50 |
| Notebooks | $0 - $100 |
| **TOTAL** | **$537 - $1,619** |

## Recovery Process

### To restart the system:

1. **Redeploy Infrastructure**:
   ```bash
   python src/infrastructure/deploy_all.py --bucket-name <your-bucket>
   ```

2. **Start Pipeline**:
   ```bash
   python start_pipeline.py
   ```

3. **Re-enable EventBridge** (if needed):
   ```bash
   aws events enable-rule --name MovieLensWeeklyRetraining
   ```

4. **Restart EC2/RDS** (if you have them):
   ```bash
   # EC2
   aws ec2 start-instances --instance-ids <instance-id>
   
   # RDS
   aws rds start-db-instance --db-instance-identifier <db-id>
   ```

## Safety Features

### Dry Run Mode
Always test first with `--dry-run`:
```bash
python stop_all_costly_resources.py --region us-east-1 --dry-run
```

This shows exactly what would be stopped without actually stopping anything.

### Confirmation Prompt
When running without `--dry-run`, you'll be asked to confirm:
```
⚠️  WARNING: This will stop/delete costly AWS resources!
Are you sure you want to continue? (yes/no):
```

Type `yes` to proceed, anything else to abort.

### Data Protection
- S3 data is NEVER deleted
- Lambda code is preserved
- IAM roles remain intact
- You can always redeploy

## Common Scenarios

### Scenario 1: End of Day (Development)
```bash
# Stop everything to avoid overnight charges
./stop_costs.sh
```

### Scenario 2: Weekend/Vacation
```bash
# Stop everything for extended period
./stop_costs.sh
```

### Scenario 3: Cost Spike Alert
```bash
# Immediately stop high-cost resources
./stop_costs.sh
```

### Scenario 4: Testing Changes
```bash
# Check what's running first
./stop_costs.sh --dry-run

# Then stop if needed
./stop_costs.sh
```

## Monitoring After Stopping

### Check AWS Console
1. Go to AWS Console → Billing Dashboard
2. Check "Cost Explorer" for today's costs
3. Should see immediate drop in hourly costs

### Verify Resources Stopped
```bash
# Check SageMaker endpoints
aws sagemaker list-endpoints

# Check EC2 instances
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"

# Check RDS instances
aws rds describe-db-instances --query 'DBInstances[?DBInstanceStatus==`available`]'
```

## Troubleshooting

### Permission Errors
If you get permission errors, ensure your IAM user/role has:
- `sagemaker:DeleteEndpoint`
- `sagemaker:StopTrainingJob`
- `sagemaker:StopNotebookInstance`
- `ec2:StopInstances`
- `rds:StopDBInstance`
- `events:DisableRule`

### Resources Won't Stop
Some resources may be protected or in use:
- Check CloudFormation stacks (may have deletion protection)
- Check for dependent resources
- Try stopping from AWS Console manually

### Script Fails Partway
The script continues even if some resources fail. Check the summary at the end to see what succeeded and what failed.

## Best Practices

1. **Always dry-run first**: `--dry-run` is your friend
2. **Stop at end of day**: If not running 24/7
3. **Monitor costs daily**: Use `check_current_costs.py`
4. **Set billing alarms**: Get notified before costs spike
5. **Document what you stop**: Know what needs restarting

## Emergency Stop

If you need to stop everything RIGHT NOW:

```bash
# No confirmation, no dry-run (use with caution)
python stop_all_costly_resources.py --region us-east-1 <<< "yes"
```

## Cost Tracking

After stopping resources, track your savings:

```bash
# Check current costs
python check_current_costs.py

# Should see significant drop within 1-2 hours
```

## Questions?

- **Q: Will I lose my data?**
  - A: No, S3 data is preserved

- **Q: Can I restart everything?**
  - A: Yes, redeploy using deployment scripts

- **Q: How long until costs drop?**
  - A: Within 1-2 hours of stopping

- **Q: What if I only want to stop endpoints?**
  - A: Modify the script or use AWS Console

- **Q: Is this reversible?**
  - A: Yes, but endpoints must be redeployed (not just restarted)

## Related Scripts

- `check_current_costs.py` - Check current AWS costs
- `AWS_COST_ANALYSIS.md` - Detailed cost breakdown
- `cleanup.sh` / `cleanup.ps1` - Full cleanup (deletes everything)
- `deploy_live.sh` - Redeploy after stopping
