# Restart Instructions - After Duplicate Job Name Fix

## What Happened

Execution 3 failed because it tried to use the same job name as Execution 2. Both executions were started within the same second, so they got the same timestamp.

**Error**: `Job name must be unique... job with this name already exists`

## Fix Applied

I've updated `start_pipeline.py` to add **milliseconds** to the timestamp, ensuring every execution gets a unique name.

**Before**: `movielens-preprocessing-20260119-155224`  
**After**: `movielens-preprocessing-20260119-160530-847` (with milliseconds)

---

## How to Restart (2 Steps)

### Step 1: Stop Failed Execution (Optional)

You can let it timeout naturally, or stop it manually:

**Option A: Via Script**
```powershell
python stop_failed_execution.py --execution-arn arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260119-155224
```

**Option B: Via AWS Console**
1. Go to: https://console.aws.amazon.com/states/home?region=us-east-1
2. Click `MovieLensMLPipeline`
3. Click execution `execution-20260119-155224`
4. Click "Stop execution" button

### Step 2: Start New Execution

```powershell
python start_pipeline.py --region us-east-1
```

This will create a new execution with unique job names!

---

## What's Different Now

### All Three Fixes Applied

1. **Input Parameters** - Added required parameters (Execution 1 fix)
2. **PassRole Permission** - Added iam:PassRole policy (Execution 2 fix)
3. **Unique Job Names** - Added milliseconds to timestamp (Execution 3 fix)

### Expected Success

**Execution 4** should complete successfully with:
- Unique job names (no collisions)
- Correct input parameters
- Proper IAM permissions

---

## Timeline of All Executions

| Execution | Time | Issue | Status |
|-----------|------|-------|--------|
| 1 | 15:20:14 | Missing input parameters | FAILED |
| 2 | 15:35:40 | Missing PassRole permission | FAILED |
| 3 | 15:52:24 | Duplicate job name | FAILED |
| **4** | **TBD** | **All fixes applied** | **READY** |

---

## After Restart

### Monitor Progress

**AWS Console** (recommended):
```
https://console.aws.amazon.com/states/home?region=us-east-1
```

**S3 Progress Check**:
```powershell
python check_s3_progress.py --bucket amzn-s3-movielens-327030626634
```

### Expected Timeline

- **Start** - Pipeline initiated
- **0-10 min** - Data Preprocessing
- **10-55 min** - Model Training (longest!)
- **55-60 min** - Model Evaluation
- **60-70 min** - Model Deployment
- **70-72 min** - Monitoring Setup
- **~72 min** - Complete!

### After Completion

```powershell
python verify_deployment.py --bucket-name amzn-s3-movielens-327030626634 --region us-east-1
```

---

## Files to Reference

- `DUPLICATE_JOB_NAME_FIX.md` - Detailed explanation of the issue
- `start_pipeline.py` - Fixed script with milliseconds
- `stop_failed_execution.py` - Script to stop failed executions
- `PIPELINE_STATUS_SUMMARY.md` - Complete monitoring guide
- `check_s3_progress.py` - Monitor via S3

---

## Quick Commands

```powershell
# Stop failed execution (optional)
python stop_failed_execution.py --execution-arn arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260119-155224

# Start new execution
python start_pipeline.py --region us-east-1

# Monitor progress
python check_s3_progress.py --bucket amzn-s3-movielens-327030626634

# After completion
python verify_deployment.py --bucket-name amzn-s3-movielens-327030626634 --region us-east-1
```

---

**Ready to restart! All three issues have been fixed.**

