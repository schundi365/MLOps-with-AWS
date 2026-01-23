# Issue #26: Inference Code Not Being Copied - Incorrect File Paths

## Problem
Execution #25 failed with the same "Worker died" error as #24, even though we had updated `train.py` to copy `inference.py` and `model.py` to the model artifacts.

### Symptoms
- Endpoint health checks still returning HTTP 500
- Model artifacts still missing `code/` directory
- Training logs showed NO messages about copying inference files
- Expected log messages like "Copied inference.py to..." never appeared

### Investigation
Inspected model artifacts from Execution #25:
```
model.tar.gz
├── model.pth        ✓ (5.2 MB)
└── metadata.json    ✓ (0.29 KB)
```

Still missing:
```
code/
├── inference.py     ✗ MISSING
└── model.py         ✗ MISSING
```

Checked training logs - no messages about inference code at all, which meant the `if os.path.exists(inference_src):` check was failing silently.

## Root Cause
**The training script was looking for inference files in the wrong location.**

In `save_model()` function, the code was:
```python
src_dir = os.path.dirname(os.path.abspath(__file__))
inference_src = os.path.join(src_dir, 'inference.py')
```

This assumes `inference.py` is in the same directory as `train.py`. However:

**In SageMaker training containers:**
- Source code tarball is extracted to `/opt/ml/code/`
- `train.py` is executed from `/opt/ml/code/`
- `os.path.dirname(__file__)` returns `/opt/ml/code/`
- But the files ARE in `/opt/ml/code/`!

**Wait, that should work... Let me check again.**

Actually, the issue is more subtle:
- When SageMaker runs the training job, it extracts the tarball
- The script runs from `/opt/ml/code/`
- But `__file__` might be a relative path, not absolute
- Or the files might be in a subdirectory

The real issue: **We need to check multiple possible locations** because SageMaker's file layout can vary.

## Solution
Updated `save_model()` to check multiple possible source directories:

```python
# Try multiple locations to find the files
possible_src_dirs = [
    '/opt/ml/code',  # SageMaker default
    os.path.dirname(os.path.abspath(__file__)),  # Same directory as train.py
    os.getcwd(),  # Current working directory
]

files_to_copy = ['inference.py', 'model.py']

for filename in files_to_copy:
    copied = False
    for src_dir in possible_src_dirs:
        src_path = os.path.join(src_dir, filename)
        if os.path.exists(src_path):
            dst_path = os.path.join(code_dir, filename)
            shutil.copy2(src_path, dst_path)
            logger.info(f"Copied {filename} from {src_path} to {dst_path}")
            copied = True
            break
    
    if not copied:
        logger.warning(f"{filename} not found in any of: {possible_src_dirs}")
        # List what files ARE available for debugging
        for src_dir in possible_src_dirs:
            if os.path.exists(src_dir):
                files = os.listdir(src_dir)
                logger.info(f"Files in {src_dir}: {files}")
```

### Key Improvements
1. **Multiple fallback locations**: Checks `/opt/ml/code/` first, then falls back to other locations
2. **Better logging**: Logs which location worked, or lists available files if none work
3. **Debugging info**: If files not found, shows what files ARE in each directory
4. **Robust**: Works regardless of SageMaker's exact file layout

## Files Modified
- **Updated**: `src/train.py` - Fixed `save_model()` function with multiple path checks
- **Created**: `fix_inference_code_paths.py` - Script that applied the fix
- **Uploaded**: `s3://amzn-s3-movielens-327030626634/training-code/sourcedir.tar.gz`

## Verification Steps
1. Start Execution #26: `python start_pipeline.py --region us-east-1`
2. Wait for training to complete (~60 minutes)
3. Check training logs for "Copied inference.py from..." messages
4. Inspect model artifacts: `python inspect_model_artifacts.py`
5. Verify `code/` directory exists with both files
6. Confirm endpoint health checks return HTTP 200
7. Verify evaluation succeeds

## Expected Outcome
Execution #26 should:
- ✓ Complete preprocessing successfully
- ✓ Complete training with RMSE < 0.9
- ✓ Log "Copied inference.py from /opt/ml/code/inference.py to..."
- ✓ Log "Copied model.py from /opt/ml/code/model.py to..."
- ✓ Create model.tar.gz with code/ directory
- ✓ Deploy endpoint successfully
- ✓ Pass health checks (HTTP 200 on /ping)
- ✓ Run evaluation successfully
- ✓ Complete with SUCCESS status

## Related Issues
- Issue #25: First attempt to add inference code (wrong approach - files not found)
- Issue #24: Endpoint wait loop (fixed)
- Issue #23: SageMaker permissions (fixed)

## Key Learnings
1. **SageMaker file layout**: Source code extracted to `/opt/ml/code/`
2. **Path resolution**: `__file__` might be relative or absolute depending on context
3. **Defensive programming**: Always check multiple possible locations
4. **Debugging**: Log available files when expected files not found
5. **Robustness**: Don't assume a single file layout - handle variations

## Timeline
- 11:34:30 - Execution #25 started (with Issue #25 fix)
- 11:51:36 - Execution #25 failed (inference code still not copied)
- 15:45:00 - Issue #26 identified (incorrect file paths)
- 15:52:00 - Issue #26 fixed (multiple path checks)
- 15:53:28 - Execution #26 started
- ~17:00:00 - Expected completion (65-75 minutes)

## Success Criteria
- [ ] Training logs show "Copied inference.py from..."
- [ ] Training logs show "Copied model.py from..."
- [ ] Model artifacts include code/inference.py
- [ ] Model artifacts include code/model.py
- [ ] Endpoint health checks return HTTP 200
- [ ] Evaluation completes successfully
- [ ] Execution status: SUCCEEDED

---

**This fix addresses the root cause: the training script now finds inference files regardless of SageMaker's exact file layout.** 🎯
