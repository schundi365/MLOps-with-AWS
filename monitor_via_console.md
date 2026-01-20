# Monitoring Your Pipeline via AWS Console

Since your IAM user doesn't have Step Functions monitoring permissions, you can use the AWS Console to monitor your pipeline execution.

## Option 1: Add Permissions (Recommended)

Run this script to add the necessary permissions:

```powershell
python add_user_permissions.py
```

This will add:
- `states:ListStateMachines`
- `states:ListExecutions`
- `states:DescribeExecution`
- `states:GetExecutionHistory`
- `states:StartExecution`

**Note**: If you don't have permission to create/attach IAM policies, ask your AWS administrator to add these permissions.

---

## Option 2: Use AWS Console (No Permissions Needed)

### Step Functions Console

1. **Open Step Functions Console**:
   - Go to: https://console.aws.amazon.com/states/home?region=us-east-1
   - Or search for "Step Functions" in AWS Console

2. **Find Your State Machine**:
   - Look for: `MovieLensMLPipeline`
   - Click on it

3. **View Executions**:
   - You'll see a list of all executions
   - Current execution: `execution-20260119-152014`
   - Status will show: Running, Succeeded, Failed, etc.

4. **View Execution Details**:
   - Click on the execution name
   - See the visual workflow with current step highlighted
   - View input/output for each step
   - Check execution timeline

5. **View Logs**:
   - Click on individual steps to see their logs
   - CloudWatch logs are linked from each step

### CloudWatch Console

1. **Open CloudWatch Console**:
   - Go to: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1

2. **View Log Groups**:
   - Navigate to "Logs" → "Log groups"
   - Look for:
     - `/aws/lambda/movielens-model-evaluation`
     - `/aws/lambda/movielens-monitoring-setup`
     - `/aws/sagemaker/TrainingJobs`

3. **View Metrics**:
   - Navigate to "Metrics" → "All metrics"
   - Look for custom metrics under "MovieLens"

---

## Option 3: Check Execution Status via Script

I'll create a simplified status checker that doesn't require Step Functions permissions:

```powershell
python check_pipeline_simple.py
```

This will check:
- S3 bucket for new files (indicates progress)
- Lambda function logs
- SageMaker training jobs

---

## Current Execution Details

**Execution ARN**: 
```
arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260119-152014
```

**Started**: January 19, 2026 at 15:20:14 UTC

**Expected Duration**: 30-60 minutes (depending on dataset size and training)

**Pipeline Steps**:
1. ✅ Start Execution
2. ⏳ Preprocessing (5-10 minutes)
3. ⏳ Training (15-30 minutes)
4. ⏳ Evaluation (2-5 minutes)
5. ⏳ Deployment (5-10 minutes)
6. ⏳ Monitoring Setup (2-3 minutes)

---

## Troubleshooting

### If Execution Fails

1. **Check CloudWatch Logs**:
   - Each step logs to CloudWatch
   - Look for error messages

2. **Check S3 Bucket**:
   - Verify data was uploaded correctly
   - Check for preprocessing outputs

3. **Check IAM Roles**:
   - Ensure roles have correct permissions
   - Verify trust relationships

### Common Issues

1. **Preprocessing Fails**:
   - Check if data was uploaded to S3
   - Verify data format is correct

2. **Training Fails**:
   - Check SageMaker training job logs
   - Verify instance type is available
   - Check for quota limits

3. **Deployment Fails**:
   - Check SageMaker endpoint logs
   - Verify instance type for hosting

---

## Quick Links

- **Step Functions Console**: https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:327030626634:stateMachine:MovieLensMLPipeline
- **S3 Bucket**: https://s3.console.aws.amazon.com/s3/buckets/amzn-s3-movielens-327030626634
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
- **SageMaker Console**: https://console.aws.amazon.com/sagemaker/home?region=us-east-1

---

## After Adding Permissions

Once you have the necessary permissions, you can use:

```powershell
# Monitor in real-time
python monitor_pipeline.py

# Check overall status
python check_deployment_status.py

# Verify everything is working
python verify_deployment.py
```
