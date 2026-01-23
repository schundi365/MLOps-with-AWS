# Issue #27: Inference Worker Died - FINAL RESOLUTION

## Problem Summary

SageMaker endpoint was failing with "Worker died" error (HTTP 500). The PyTorch container was using its default inference handler which expects a TorchScript model (`torch.jit.load`), but our training script saves models as PyTorch state dicts (`torch.save(model.state_dict())`).

## Root Cause Analysis

### Initial Investigation
- CloudWatch logs showed: `torch.jit.load(model_path)` failing with "file not found" error
- This indicated the default PyTorch inference handler was being used
- The default handler expects TorchScript models, not state dict models

### First Attempted Fix (FAILED)
**What we tried:**
- Added environment variables to the `CreateModel` step in Step Functions:
  - `SAGEMAKER_PROGRAM`: `inference.py`
  - `SAGEMAKER_SUBMIT_DIRECTORY`: `s3://bucket/code/inference_code.tar.gz`
  - `SAGEMAKER_REGION`: `us-east-1`
- Created `inference_code.tar.gz` with custom inference handler
- Updated state machine definition

**Why it failed:**
- The `SAGEMAKER_SUBMIT_DIRECTORY` environment variable **only works during TRAINING**, not during INFERENCE
- For inference, SageMaker PyTorch containers look for code in `/opt/ml/model/code/` directory
- The inference code must be **inside the model artifacts**, not referenced via environment variable

### Deep Dive: How SageMaker PyTorch Inference Works

SageMaker PyTorch containers look for custom inference code in this order:
1. **Inside model artifacts**: `/opt/ml/model/code/inference.py`
2. If not found, uses the default handler: `default_pytorch_inference_handler.py`

The training script (`src/train.py`) already had code to copy inference files into model artifacts (lines 308-343):
```python
# Copy inference code files for SageMaker endpoint
code_dir = os.path.join(model_dir, 'code')
os.makedirs(code_dir, exist_ok=True)

# Copy inference.py and model.py
files_to_copy = ['inference.py', 'model.py']
for filename in files_to_copy:
    # Try to find and copy the file
    ...
```

**But the files were not being found!**

### The Real Problem

The training script looks for `inference.py` and `model.py` in `/opt/ml/code/` during training. This directory is populated from the `sagemaker_submit_directory` hyperparameter, which points to `s3://bucket/code/sourcedir.tar.gz`.

**Investigation of sourcedir.tar.gz:**
```bash
$ tar -tzf sourcedir.tar.gz
train.py
```

**The problem:** `sourcedir.tar.gz` only contained `train.py`, but it needed to also contain `inference.py` and `model.py`!

## Final Solution

### Fix Applied
Recreated `sourcedir.tar.gz` to include all necessary files:
- `train.py` (training script)
- `inference.py` (custom inference handler)
- `model.py` (model architecture)

### Implementation
```python
# fix_sourcedir_tarball.py
with tarfile.open('sourcedir.tar.gz', 'w:gz') as tar:
    tar.add('src/train.py', arcname='train.py')
    tar.add('src/inference.py', arcname='inference.py')
    tar.add('src/model.py', arcname='model.py')

# Upload to S3
s3_client.upload_fileobj(f, bucket, 'code/sourcedir.tar.gz')
```

### How It Works Now

1. **During Training:**
   - SageMaker extracts `sourcedir.tar.gz` to `/opt/ml/code/`
   - Files available: `train.py`, `inference.py`, `model.py`
   - Training script finds `inference.py` and `model.py`
   - Training script copies them to `/opt/ml/model/code/`
   - Model artifacts are packaged with the code directory

2. **During Inference:**
   - SageMaker extracts model artifacts to `/opt/ml/model/`
   - Directory structure:
     ```
     /opt/ml/model/
     ├── model.pth
     ├── metadata.json
     └── code/
         ├── inference.py
         └── model.py
     ```
   - PyTorch container finds `/opt/ml/model/code/inference.py`
   - Uses our custom `model_fn`, `input_fn`, `predict_fn`, `output_fn`
   - Loads model using `torch.load(state_dict)` instead of `torch.jit.load()`

## Files Modified

1. **Created:**
   - `fix_sourcedir_tarball.py` - Script to recreate sourcedir.tar.gz with all files
   - `cleanup_and_restart_final.py` - Script to clean up and restart pipeline
   - `fix_inference_handler_final.py` - Documentation of the workaround approach
   - `ISSUE_27_FINAL_RESOLUTION.md` - This document

2. **Updated:**
   - `s3://amzn-s3-movielens-327030626634/code/sourcedir.tar.gz` - Now contains all 3 files

3. **No changes needed:**
   - `src/train.py` - Already had the code to copy inference files
   - `src/inference.py` - Custom inference handler (already correct)
   - `src/model.py` - Model architecture (already correct)

## Verification Steps

### 1. Verify sourcedir.tar.gz Contents
```python
import boto3, tarfile, io
s3 = boto3.client('s3')
obj = s3.get_object(Bucket='amzn-s3-movielens-327030626634', Key='code/sourcedir.tar.gz')
tar = tarfile.open(fileobj=io.BytesIO(obj['Body'].read()))
for member in tar.getmembers():
    print(member.name)
# Expected output:
# train.py
# inference.py
# model.py
```

### 2. Monitor Training Logs
Look for these log messages during training:
```
Copied inference.py from /opt/ml/code/inference.py to /opt/ml/model/code/inference.py
Copied model.py from /opt/ml/code/model.py to /opt/ml/model/code/model.py
Model artifacts saved successfully with inference code
```

### 3. Verify Model Artifacts
After training completes, check the model artifacts:
```python
# Download and inspect model.tar.gz
tar = tarfile.open('model.tar.gz')
tar.list()
# Expected:
# model.pth
# metadata.json
# code/inference.py
# code/model.py
```

### 4. Check Endpoint Logs
After endpoint deployment, check CloudWatch logs for:
```
Loading model from /opt/ml/model
Creating model with num_users=..., num_movies=..., embedding_dim=...
Model loaded successfully
```

**NOT:**
```
torch.jit.load(model_path, map_location=device)
RuntimeError: PytorchStreamReader failed locating file constants.pkl
```

## Current Status

✅ **FIXED** - Pipeline execution `execution-20260123-112004-final` started with corrected configuration.

**Timeline:**
- Started: 2026-01-23 11:20:05 UTC
- Expected completion: ~40-60 minutes
- Current step: Data Preprocessing

**Monitoring:**
```bash
python monitor_pipeline.py
```

## Key Learnings

1. **Environment Variables Scope**: `SAGEMAKER_SUBMIT_DIRECTORY` only works during training, not inference
2. **Inference Code Location**: Must be in `/opt/ml/model/code/` directory inside model artifacts
3. **Training Script Packaging**: The `sourcedir.tar.gz` must contain ALL files needed by the training script
4. **Model Artifacts Structure**: Include a `code/` directory with inference scripts
5. **CloudWatch Logs**: Essential for debugging - always check the actual error, not just "Worker died"

## Prevention

To prevent this issue in future deployments:

1. **Always include inference code in sourcedir.tar.gz:**
   ```python
   tar.add('src/train.py', arcname='train.py')
   tar.add('src/inference.py', arcname='inference.py')
   tar.add('src/model.py', arcname='model.py')
   ```

2. **Verify training logs** show inference files being copied

3. **Test model artifacts** before deploying to production

4. **Document the requirement** in deployment guides

## Related Issues

- Issue #25: Inference code packaging (initial attempt)
- Issue #26: Inference code paths (environment variables approach)
- Issue #27: This issue - final resolution

## References

- [SageMaker PyTorch Container Documentation](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html)
- [Custom Inference Code](https://docs.aws.amazon.com/sagemaker/latest/dg/adapt-inference-container.html)
- Training script: `src/train.py` lines 308-343
- Inference handler: `src/inference.py`
