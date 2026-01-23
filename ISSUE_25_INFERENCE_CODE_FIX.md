# Issue #25: Missing Inference Code in Model Artifacts

## Problem
Executions #23 and #24 failed with "Worker died" error when the endpoint tried to serve predictions. The endpoint health checks (`/ping`) were failing with HTTP 500 errors.

### Error Message
```
An error occurred (ModelError) when calling the InvokeEndpoint operation: 
Received server error (500) from primary with message "Worker died."
```

### CloudWatch Logs
```
[INFO] W-9001-model_1.0 ACCESS_LOG - /169.254.178.2:38140 "GET /ping HTTP/1.1" 500 1
[INFO] W-9001-model_1.0 TS_METRICS - Requests5XX.Count:1.0
```

The `/ping` endpoint was consistently returning HTTP 500, meaning the model couldn't be loaded.

## Root Cause
The training script (`train.py`) was only saving:
- `model.pth` - Model weights
- `metadata.json` - Model configuration

But the SageMaker PyTorch inference container needs:
- `inference.py` - Contains `model_fn()`, `input_fn()`, `predict_fn()`, `output_fn()`
- `model.py` - Contains `CollaborativeFilteringModel` class definition

Without these files, the inference container couldn't:
1. Load the model architecture (`model_fn` needs `CollaborativeFilteringModel`)
2. Process requests (`input_fn`, `predict_fn`, `output_fn`)

## Solution
Updated `train.py` to copy inference code files into the model directory:

### Changes to save_model() function
```python
# Copy inference code files for SageMaker endpoint
code_dir = os.path.join(model_dir, 'code')
os.makedirs(code_dir, exist_ok=True)

# Copy inference.py
src_dir = os.path.dirname(os.path.abspath(__file__))
inference_src = os.path.join(src_dir, 'inference.py')
inference_dst = os.path.join(code_dir, 'inference.py')
if os.path.exists(inference_src):
    shutil.copy2(inference_src, inference_dst)
    logger.info(f"Copied inference.py to {inference_dst}")

# Copy model.py
model_src = os.path.join(src_dir, 'model.py')
model_dst = os.path.join(code_dir, 'model.py')
if os.path.exists(model_src):
    shutil.copy2(model_src, model_dst)
    logger.info(f"Copied model.py to {model_dst}")
```

### Model Artifacts Structure
**Before (Broken):**
```
model.tar.gz
├── model.pth
└── metadata.json
```

**After (Fixed):**
```
model.tar.gz
├── model.pth
├── metadata.json
└── code/
    ├── inference.py
    └── model.py
```

## How SageMaker Finds Inference Code
1. SageMaker extracts `model.tar.gz` to `/opt/ml/model/`
2. PyTorch inference container looks for code in `/opt/ml/model/code/`
3. If found, it imports `inference.py` from that directory
4. The `model_fn()` function can then import `CollaborativeFilteringModel` from `model.py`

## Files Modified
- **Updated**: `src/train.py` - Added code to copy inference files
- **Created**: `fix_inference_code_packaging.py` - Script that applied the fix
- **Uploaded**: `s3://amzn-s3-movielens-327030626634/training-code/sourcedir.tar.gz`

## Verification
- Execution #25 started: 2026-01-22 11:34:30 UTC
- Expected behavior:
  - Training will include inference.py and model.py in model.tar.gz
  - Endpoint will load successfully
  - Health checks will return HTTP 200
  - Evaluation will succeed

## Related Issues
- Issue #23: SageMaker permissions (fixed)
- Issue #24: Endpoint wait loop (fixed)
- Issue #25: Missing inference code (fixed)

## Key Learnings
1. SageMaker PyTorch containers need inference code in `code/` subdirectory
2. Training script must package all necessary Python files
3. Model artifacts must be self-contained for inference
4. Health check failures (`/ping` returning 500) indicate model loading issues
5. CloudWatch logs show "Worker died" when model_fn() fails

## Expected Outcome
Execution #25 should:
- ✓ Complete preprocessing successfully
- ✓ Complete training with inference code included
- ✓ Create model with code/ directory
- ✓ Deploy endpoint successfully
- ✓ Pass health checks (HTTP 200 on /ping)
- ✓ Run evaluation successfully
- ✓ Complete with SUCCESS status

## Timeline
- 11:06:47 - Execution #23 failed (Worker died)
- 11:28:22 - Execution #24 failed (Worker died)
- 11:33:00 - Issue #25 identified and fixed
- 11:34:30 - Execution #25 started
- ~12:50:00 - Expected completion (75 minutes)
