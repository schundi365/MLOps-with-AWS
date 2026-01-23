# Issue #27: Inference Worker Died - Model Loading Error

## Problem

SageMaker endpoint was failing with "Worker died" error (HTTP 500) during health checks:

```
"errorMessage": "An error occurred (ModelError) when calling the InvokeEndpoint operation: 
Received server error (500) from primary with message \"Worker died.\""
```

## Root Cause

The CloudWatch logs revealed the actual error:

```python
File "/opt/conda/lib/python3.10/site-packages/sagemaker_pytorch_serving_container/default_pytorch_inference_handler.py", line 78, in default_model_fn
    model = torch.jit.load(model_path, map_location=device)
```

**The Issue**: The SageMaker PyTorch container was using its default inference handler, which expects a TorchScript model (`torch.jit.load`), but our training script saves the model as a regular PyTorch state dict (`torch.save(model.state_dict())`).

## Solution

Added environment variables to the `CreateModel` step in the Step Functions state machine to tell SageMaker to use our custom inference handler:

```python
container['Environment'] = {
    'SAGEMAKER_PROGRAM': 'inference.py',
    'SAGEMAKER_SUBMIT_DIRECTORY': 's3://amzn-s3-movielens-327030626634/code/inference_code.tar.gz',
    'SAGEMAKER_REGION': 'us-east-1'
}
```

## Implementation Steps

### 1. Package Inference Code

Created a tarball containing our custom inference handler:
- `src/inference.py` - Custom inference functions (model_fn, input_fn, predict_fn, output_fn)
- `src/model.py` - Model architecture definition

```bash
tar -czf inference_code.tar.gz src/inference.py src/model.py
```

### 2. Upload to S3

```bash
aws s3 cp inference_code.tar.gz s3://amzn-s3-movielens-327030626634/code/
```

### 3. Update State Machine

Modified the `CreateModel` step in the Step Functions definition to include the environment variables that point to our custom inference code.

### 4. Restart Pipeline

```bash
python cleanup_and_restart.py
```

## Files Modified

- `fix_inference_entry_point.py` - Script to apply the fix
- `cleanup_and_restart.py` - Script to clean up failed resources and restart
- `start_pipeline_with_correct_input.py` - Updated to provide all required input fields

## Verification

After applying the fix:
1. ✅ Data Preprocessing completed successfully
2. 🔄 Model Training is running (in progress)
3. Next: Model will be deployed with custom inference handler

## Key Learnings

1. **SageMaker Container Defaults**: PyTorch containers have default handlers that expect specific model formats
2. **Custom Handlers**: Always specify `SAGEMAKER_PROGRAM` and `SAGEMAKER_SUBMIT_DIRECTORY` when using custom inference code
3. **Model Format Mismatch**: Ensure training and inference code use compatible model serialization formats
4. **CloudWatch Logs**: Essential for debugging endpoint failures - check `/aws/sagemaker/Endpoints/<endpoint-name>` log group

## Related Issues

- Issue #25: Inference code packaging
- Issue #26: Inference code paths

## Status

✅ **RESOLVED** - Pipeline execution `execution-20260122-162230-4567` is progressing with the fixed configuration.

## Next Steps

1. Monitor training completion (~30-45 minutes)
2. Verify endpoint deployment succeeds
3. Test inference with sample predictions
4. Validate P99 latency < 500ms requirement
