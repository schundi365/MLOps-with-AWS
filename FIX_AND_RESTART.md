# Fix and Restart - Preprocessing Code Issue

## Problem

Pipeline failed because the preprocessing script wasn't uploaded to S3 for the SageMaker processing job.

**Error**: `python3: can't open file '/opt/ml/processing/input/preprocessing.py': [Errno 2] No such file or directory`

---

## Quick Fix (3 Commands)

### 1. Upload Preprocessing Code

```powershell
python upload_preprocessing_code.py --bucket amzn-s3-movielens-327030626634
```

### 2. Update State Machine

```powershell
python fix_preprocessing_input.py --bucket amzn-s3-movielens-327030626634
```

### 3. Restart Pipeline

```powershell
python start_pipeline.py --region us-east-1
```

---

## What Each Step Does

**Step 1**: Uploads `src/preprocessing.py` to `s3://bucket/code/preprocessing.py`

**Step 2**: Updates Step Functions to:
- Include preprocessing code as an input
- Fix file paths in the container
- Update the entrypoint command

**Step 3**: Starts a new pipeline execution with all fixes applied

---

## All Issues Fixed

| # | Issue | Status |
|---|-------|--------|
| 1 | Missing input parameters | ✓ Fixed |
| 2 | Missing PassRole permission | ✓ Fixed |
| 3 | Duplicate job names | ✓ Fixed |
| 4 | Missing preprocessing code | ✓ Fix ready |

**After running the 3 commands above, all issues will be resolved!**

---

## Expected Timeline

- **0-10 min**: Data Preprocessing
- **10-55 min**: Model Training (longest!)
- **55-60 min**: Model Evaluation
- **60-70 min**: Model Deployment
- **70-72 min**: Monitoring Setup
- **~72 min**: Complete!

---

## Monitor Progress

**AWS Console**:
```
https://console.aws.amazon.com/states/home?region=us-east-1
```

**S3 Progress Check**:
```powershell
python check_s3_progress.py --bucket amzn-s3-movielens-327030626634
```

---

## After Completion

```powershell
python verify_deployment.py --bucket-name amzn-s3-movielens-327030626634 --region us-east-1
```

---

**Run the 3 commands above to fix and restart!**

