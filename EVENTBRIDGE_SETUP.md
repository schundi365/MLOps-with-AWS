# EventBridge Permissions Setup

This guide helps you add EventBridge permissions to enable automated weekly retraining.

## Why EventBridge?

EventBridge allows the system to automatically trigger the ML pipeline every Sunday at 2 AM UTC for weekly model retraining. Without it, you'll need to manually trigger retraining via the AWS Console.

## Option 1: Automated Script (Recommended)

Run the automated script to add permissions:

```powershell
# Auto-detect your current user
python src\infrastructure\add_eventbridge_permissions.py --auto

# Or specify user name explicitly
python src\infrastructure\add_eventbridge_permissions.py --user-name dev
```

**What it does:**
- Adds EventBridge permissions to your IAM user
- Allows creating and managing scheduled rules
- Enables automated weekly retraining

**If you get "AccessDenied":**
- You don't have permission to modify IAM policies
- Use Option 2 or Option 3 below

## Option 2: AWS Console (Manual)

### Step 1: Open IAM Console
1. Go to AWS Console → IAM
2. Click "Users" in the left sidebar
3. Click on your user (e.g., "dev")

### Step 2: Add Inline Policy
1. Click the "Permissions" tab
2. Click "Add permissions" → "Create inline policy"
3. Click the "JSON" tab
4. Paste this policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "events:PutRule",
                "events:PutTargets",
                "events:DescribeRule",
                "events:DeleteRule",
                "events:RemoveTargets",
                "events:ListRules",
                "events:ListTargetsByRule"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "events.amazonaws.com"
                }
            }
        }
    ]
}
```

5. Click "Review policy"
6. Name it: `EventBridgeDeploymentAccess`
7. Click "Create policy"

### Step 3: Verify
Run the deployment again without `--skip-eventbridge`:

```powershell
python src\infrastructure\deploy_all.py --bucket-name movielens-ml-327030626634 --region us-east-1
```

## Option 3: AWS CLI

If you have admin access, use AWS CLI:

```powershell
# Create policy document
$policy = @"
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "events:PutRule",
                "events:PutTargets",
                "events:DescribeRule",
                "events:DeleteRule",
                "events:RemoveTargets",
                "events:ListRules",
                "events:ListTargetsByRule"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "iam:PassRole"
            ],
            "Resource": "*",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "events.amazonaws.com"
                }
            }
        }
    ]
}
"@

# Add policy to user
aws iam put-user-policy --user-name dev --policy-name EventBridgeDeploymentAccess --policy-document $policy
```

## Option 4: Skip EventBridge (No Automation)

If you can't get EventBridge permissions, you can deploy without it:

```powershell
python src\infrastructure\deploy_all.py --bucket-name movielens-ml-327030626634 --region us-east-1 --skip-eventbridge
```

**Trade-off:**
- ✅ Deployment works without additional permissions
- ❌ No automated weekly retraining
- ℹ️ You'll need to manually trigger the pipeline via AWS Console

### Manual Trigger Steps:
1. Go to AWS Console → Step Functions
2. Find "MovieLensMLPipeline"
3. Click "Start execution"
4. Click "Start execution" again (no input needed)

## Verify EventBridge Setup

After adding permissions, verify the EventBridge rule was created:

```powershell
aws events describe-rule --name MovieLensWeeklyRetraining
```

Expected output:
```json
{
    "Name": "MovieLensWeeklyRetraining",
    "Arn": "arn:aws:events:us-east-1:327030626634:rule/MovieLensWeeklyRetraining",
    "State": "ENABLED",
    "ScheduleExpression": "cron(0 2 ? * SUN *)",
    "Description": "Trigger MovieLens ML pipeline weekly retraining"
}
```

## Troubleshooting

### "AccessDenied" when running the script
**Problem:** You don't have permission to modify IAM policies  
**Solution:** Ask your AWS administrator to add the permissions, or use Option 2 (AWS Console)

### "User does not exist"
**Problem:** Wrong user name specified  
**Solution:** Check your user name with `aws sts get-caller-identity`

### EventBridge rule not triggering
**Problem:** Rule created but not firing  
**Solution:** 
1. Check rule is ENABLED: `aws events describe-rule --name MovieLensWeeklyRetraining`
2. Check targets are attached: `aws events list-targets-by-rule --rule MovieLensWeeklyRetraining`
3. Check Step Functions execution history in AWS Console

## Next Steps

After adding EventBridge permissions:

1. **Re-run deployment** (without --skip-eventbridge):
   ```powershell
   python src\infrastructure\deploy_all.py --bucket-name movielens-ml-327030626634 --region us-east-1
   ```

2. **Upload dataset**:
   ```powershell
   python src\data_upload.py --dataset 100k --bucket movielens-ml-327030626634 --prefix raw-data/
   ```

3. **Start first training** (manual):
   - Go to Step Functions console
   - Click "MovieLensMLPipeline"
   - Click "Start execution"

4. **Automated retraining** will happen every Sunday at 2 AM UTC

## Summary

| Option | Pros | Cons | Best For |
|--------|------|------|----------|
| **Automated Script** | Fast, easy | Requires IAM permissions | Users with IAM access |
| **AWS Console** | Visual, guided | Manual steps | Users without CLI access |
| **AWS CLI** | Scriptable | Requires admin access | DevOps/automation |
| **Skip EventBridge** | No permissions needed | No automation | Testing/development |

Choose the option that works best for your AWS permissions level!
