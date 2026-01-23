# Monitor Execution #19 - Quick Reference

## Execution Details

**ARN**: `arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260121-125239-480`  
**Started**: 2026-01-21 12:52:40 UTC  
**Expected End**: 2026-01-21 14:14:00 UTC

---

## Quick Status Check

```powershell
python check_execution_status.py --execution-arn "arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260121-125239-480"
```

---

## Timeline & Checkpoints

### Checkpoint 1: Preprocessing (13:02 UTC)
**Expected**: Preprocessing complete, training starts

**Check**:
```powershell
python check_execution_status.py --execution-arn "arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260121-125239-480"
```

**Expected Output**:
```
Current State: ModelTraining
```

**If Failed**: Check preprocessing logs
```powershell
python check_preprocessing_logs.py
```

---

### Checkpoint 2: Training Progress (13:30 UTC)
**Expected**: Training ~50% complete

**Check**: AWS Console
```
https://console.aws.amazon.com/sagemaker/home?region=us-east-1#/jobs
```

**Look For**:
- Job status: InProgress
- Training time: ~30 minutes
- Logs showing epoch progress

---

### Checkpoint 3: Training Complete (14:02 UTC)
**Expected**: Training complete, evaluation starts

**Check**:
```powershell
python check_execution_status.py --execution-arn "arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260121-125239-480"
```

**Expected Output**:
```
Current State: ModelEvaluation
```

**If Failed**: Check training logs
```powershell
python get_training_logs.py <job-name>
```

---

### Checkpoint 4: Evaluation Complete (14:07 UTC)
**Expected**: Evaluation complete, deployment starts

**CRITICAL CHECK**: Lambda logs for numpy import
```powershell
python check_lambda_error.py
```

**Expected Output**:
```
[INFO] Starting model evaluation
[INFO] Loading test data from s3://...
[INFO] Loaded 20000 test samples
[INFO] Invoking endpoint...
[INFO] RMSE: 0.85
[INFO] MAE: 0.67
[INFO] Model evaluation completed successfully
```

**If Failed**: Numpy import error means Issue #19 not fully fixed

---

### Checkpoint 5: Deployment Complete (14:12 UTC)
**Expected**: Deployment complete, monitoring starts

**Check**:
```powershell
python check_execution_status.py --execution-arn "arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260121-125239-480"
```

**Expected Output**:
```
Current State: MonitoringSetup
```

---

### Checkpoint 6: SUCCESS! (14:14 UTC)
**Expected**: Execution complete!

**Check**:
```powershell
python check_execution_status.py --execution-arn "arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260121-125239-480"
```

**Expected Output**:
```
Status: SUCCEEDED
```

**Verify Deployment**:
```powershell
python verify_deployment.py --bucket-name amzn-s3-movielens-327030626634 --region us-east-1
```

**Test Predictions**:
```powershell
python test_predictions.py
```

---

## AWS Console Links

### Step Functions
```
https://console.aws.amazon.com/states/home?region=us-east-1#/executions/details/arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260121-125239-480
```

### SageMaker Training Jobs
```
https://console.aws.amazon.com/sagemaker/home?region=us-east-1#/jobs
```

### Lambda Logs
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups/log-group/$252Faws$252Flambda$252Fmovielens-model-evaluation
```

### S3 Bucket
```
https://s3.console.aws.amazon.com/s3/buckets/amzn-s3-movielens-327030626634?region=us-east-1
```

---

## Troubleshooting

### If Preprocessing Fails
1. Check S3 raw data exists
2. Verify IAM permissions
3. Check preprocessing logs
4. Review data format

### If Training Fails
1. Check training logs
2. Verify code uploaded to S3
3. Check instance type (ml.m5.xlarge)
4. Review hyperparameters

### If Evaluation Fails
1. **CHECK LAMBDA LOGS FIRST**
2. Verify numpy imports correctly
3. Check test data exists
4. Verify endpoint name
5. Check IAM permissions

### If Deployment Fails
1. Check SageMaker permissions
2. Verify model artifacts exist
3. Check endpoint configuration
4. Review CloudWatch logs

---

## What to Watch For

### Good Signs
- [x] Preprocessing completes in ~10 minutes
- [ ] Training completes in ~60 minutes
- [ ] Lambda logs show successful import
- [ ] Evaluation calculates RMSE
- [ ] Endpoint deploys successfully
- [ ] Monitoring setup completes

### Warning Signs
- [ ] Preprocessing takes >15 minutes
- [ ] Training fails with resource error
- [ ] Lambda shows import error
- [ ] Evaluation times out
- [ ] Endpoint fails to deploy

---

## Expected Metrics

### Training
- **RMSE**: ~0.85-0.90
- **MAE**: ~0.65-0.70
- **Epochs**: 50
- **Duration**: ~60 minutes

### Evaluation
- **Test Samples**: ~20,000
- **RMSE**: <0.9 (target)
- **MAE**: <0.7 (target)
- **Duration**: ~5 minutes

### Endpoint
- **Instance**: ml.m5.xlarge
- **Latency**: <500ms (target)
- **Auto-scaling**: 1-5 instances
- **Duration**: ~5 minutes to deploy

---

## Success Checklist

After execution completes:

- [ ] Execution status: SUCCEEDED
- [ ] Preprocessing: SUCCESS
- [ ] Training: SUCCESS
- [ ] Evaluation: SUCCESS
- [ ] Deployment: SUCCESS
- [ ] Monitoring: SUCCESS
- [ ] Endpoint: InService
- [ ] Test predictions: Working
- [ ] Metrics: Stored in S3
- [ ] Dashboard: Created

---

## Quick Commands Reference

```powershell
# Check execution status
python check_execution_status.py --execution-arn "arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260121-125239-480"

# Check Lambda logs
python check_lambda_error.py

# Verify deployment
python verify_deployment.py --bucket-name amzn-s3-movielens-327030626634 --region us-east-1

# Test predictions
python test_predictions.py

# Check S3 progress
python check_s3_progress.py
```

---

**Monitor closely at 14:02 UTC for Lambda evaluation!**  
**That's when we'll know if Issue #19 is truly fixed!**

**Good luck!**
