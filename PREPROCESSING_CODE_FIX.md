# Preprocessing Code Fix - Missing Script Issue

## Problem Identified

**Execution 4** failed during the DataPreprocessing step with error:

```
python3: can't open file '/opt/ml/processing/input/preprocessing.py': [Errno 2] No such file or directory
```

## Root Cause

The Step Functions state machine configuration only uploads the **raw data** to the SageMaker processing job, but not the **preprocessing code** itself.

### Current Configuration (Broken)

```json
"ProcessingInputs": [
    {
        "InputName": "raw-data",
        "S3Input": {
            "S3Uri": "s3://bucket/raw-data/",
            "LocalPath": "/opt/ml/processing/input"
        }
    }
]
```

This only uploads data files, not the Python script.

### What's Missing

The preprocessing script (`src/preprocessing.py`) needs to be:
1. Uploaded to S3
2. Included as an input to the processing job
3. Referenced with the correct path in the container entrypoint

## Fix Required (3 Steps)

### Step 1: Upload Preprocessing Code to S3

```powershell
python upload_preprocessing_code.py --bucket amzn-s3-movielens-327030626634
```

This uploads `src/preprocessing.py` to `s3://bucket/code/preprocessing.py`

### Step 2: Update Step Functions State Machine

```powershell
python fix_preprocessing_input.py --bucket amzn-s3-movielens-327030626634
```

This updates the state machine to:
- Add preprocessing code as an input
- Update paths for data and code
- Fix the container entrypoint

### Step 3: Restart Pipeline

```powershell
python start_pipeline.py --region us-east-1
```

## What the Fix Does

### Updated Configuration (Fixed)

```json
"ProcessingInputs": [
    {
        "InputName": "code",
        "S3Input": {
            "S3Uri": "s3://bucket/code/preprocessing.py",
            "LocalPath": "/opt/ml/processing/input/code"
        }
    },
    {
        "InputName": "raw-data",
        "S3Input": {
            "S3Uri": "s3://bucket/raw-data/",
            "LocalPath": "/opt/ml/processing/input/data"
        }
    }
]
```

### Updated Entrypoint

**Before**: `["python3", "/opt/ml/processing/input/preprocessing.py"]`  
**After**: `["python3", "/opt/ml/processing/input/code/preprocessing.py"]`

### File Structure in Container

```
/opt/ml/processing/
├── input/
│   ├── code/
│   │   └── preprocessing.py          ← Processing script
│   └── data/
│       ├── u.data                     ← Raw data files
│       ├── u.item
│       ├── u.user
│       └── u.genre
└── output/
    ├── train.csv                      ← Output files
    ├── validation.csv
    └── test.csv
```

## Timeline of All Issues & Fixes

| Execution | Time | Issue | Fix |
|-----------|------|-------|-----|
| 1 | 15:20:14 | Missing input parameters | Added parameters |
| 2 | 15:35:40 | Missing PassRole permission | Added IAM policy |
| 3 | 15:52:24 | Duplicate job name | Added milliseconds |
| 4 | TBD | Missing preprocessing code | Upload code + update state machine |
| **5** | **TBD** | **All fixes applied** | **Should succeed!** |

## Why This Was Missing

The initial deployment assumed the preprocessing code would be:
1. Baked into a custom Docker image, OR
2. Installed as a package in the container, OR
3. Available in the SageMaker image

In reality:
- We're using a standard SageMaker scikit-learn image
- Our custom code needs to be provided as an input
- SageMaker processing jobs require explicit code inputs

## Files Created

1. `upload_preprocessing_code.py` - Upload preprocessing script to S3
2. `fix_preprocessing_input.py` - Update state machine configuration
3. `PREPROCESSING_CODE_FIX.md` - This documentation

## Alternative Solutions

### Option 1: Custom Docker Image (More Complex)
- Build custom Docker image with preprocessing code
- Push to ECR
- Update state machine to use custom image
- Pros: Code is baked in, no S3 upload needed
- Cons: Requires Docker build/push, slower iteration

### Option 2: Code Input (Current Solution)
- Upload code to S3
- Include as processing input
- Pros: Simple, fast iteration, no Docker needed
- Cons: Requires S3 upload step

### Option 3: Python Package
- Package code as Python wheel
- Install in container at runtime
- Pros: Standard Python packaging
- Cons: Requires package build, slower startup

**Current solution (Option 2) is best for rapid development and iteration.**

## Prevention for Future

### Update Infrastructure Deployment

The `src/infrastructure/stepfunctions_deployment.py` should be updated to include code inputs by default:

```python
"ProcessingInputs": [
    {
        "InputName": "code",
        "S3Input": {
            "S3Uri": f"s3://{bucket_name}/code/preprocessing.py",
            "LocalPath": "/opt/ml/processing/input/code",
            "S3DataType": "S3Prefix",
            "S3InputMode": "File"
        }
    },
    {
        "InputName": "raw-data",
        "S3Input": {
            "S3Uri": f"s3://{bucket_name}/raw-data/",
            "LocalPath": "/opt/ml/processing/input/data",
            "S3DataType": "S3Prefix",
            "S3InputMode": "File"
        }
    }
]
```

### Add to Deployment Checklist

1. Upload raw data to S3
2. **Upload preprocessing code to S3** ← NEW
3. Deploy infrastructure
4. Start pipeline

## Lessons Learned

1. **SageMaker processing jobs need explicit code inputs** - code isn't automatically available
2. **Test with actual SageMaker jobs** - local testing doesn't catch this
3. **Document all S3 uploads required** - not just data, but code too
4. **Use standard images carefully** - they don't include custom code
5. **Separate code and data paths** - cleaner organization

## Next Steps

1. **Upload preprocessing code**:
   ```powershell
   python upload_preprocessing_code.py --bucket amzn-s3-movielens-327030626634
   ```

2. **Update state machine**:
   ```powershell
   python fix_preprocessing_input.py --bucket amzn-s3-movielens-327030626634
   ```

3. **Restart pipeline**:
   ```powershell
   python start_pipeline.py --region us-east-1
   ```

4. **Monitor via AWS Console**:
   ```
   https://console.aws.amazon.com/states/home?region=us-east-1
   ```

5. **Expected completion**: ~72 minutes after start

---

**Status**: FIX READY - Run the 3 steps above to resolve the issue

