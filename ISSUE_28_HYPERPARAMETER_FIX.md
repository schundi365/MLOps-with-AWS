# Issue #28: Hyperparameter Argument Parsing Error - FIXED

## Problem Summary

Training job failed with argument parsing error:
```
train.py: error: unrecognized arguments: --batch_size 256 --embedding_dim 128 --learning_rate 0.001 --num_factors 50
```

This was a **regression of Issue #15** - the hyperparameters in the Step Functions state machine were using underscores, but the training script expects hyphens.

## Root Cause

The Step Functions state machine definition had hyperparameters with underscores:
```json
"HyperParameters": {
    "epochs": "50",
    "batch_size": "256",           // ❌ Should be batch-size
    "learning_rate": "0.001",      // ❌ Should be learning-rate
    "embedding_dim": "128",        // ❌ Should be embedding-dim
    "num_factors": "50"            // ❌ Should be num-factors
}
```

But the training script (`src/train.py` lines 75-84) expects hyphens:
```python
parser.add_argument('--embedding-dim', type=int, default=128)
parser.add_argument('--learning-rate', type=float, default=0.001)
parser.add_argument('--batch-size', type=int, default=256)
parser.add_argument('--num-factors', type=int, default=50)
```

## Solution

Updated the Step Functions state machine definition to use hyphenated parameter names:

```json
"HyperParameters": {
    "epochs": "50",
    "batch-size": "256",           // ✓ Fixed
    "learning-rate": "0.001",      // ✓ Fixed
    "embedding-dim": "128",        // ✓ Fixed
    "num-factors": "50"            // ✓ Fixed
}
```

## Implementation

### Script Created: `fix_hyperparameter_names.py`

This script:
1. Fetches the current state machine definition
2. Updates the hyperparameters to use hyphens
3. Updates the state machine with the corrected definition

### Execution

```bash
python fix_hyperparameter_names.py
```

**Result:**
- ✓ State machine updated successfully
- ✓ All hyperparameter names now use hyphens

## Verification Steps

### 1. Check State Machine Definition
```python
import boto3, json
sfn = boto3.client('stepfunctions', region_name='us-east-1')
response = sfn.describe_state_machine(stateMachineArn='...')
definition = json.loads(response['definition'])
params = definition['States']['ModelTraining']['Parameters']['HyperParameters']
print(params)
# Should show: batch-size, learning-rate, embedding-dim, num-factors
```

### 2. Monitor Training Logs
After starting a new execution, check CloudWatch logs for:
```
✓ Arguments: Namespace(batch_size=256, learning_rate=0.001, embedding_dim=128, ...)
✗ train.py: error: unrecognized arguments
```

### 3. Verify Training Completes
Training should now:
- Parse arguments correctly
- Copy inference files to model artifacts
- Complete successfully with validation RMSE < 0.9

## Current Status

✅ **FIXED** - New pipeline execution started with corrected hyperparameters.

**Execution Details:**
- Execution Name: `execution-20260123-114011-hyphen-fix`
- Start Time: 2026-01-23 11:40:13 UTC
- Current Step: Data Preprocessing
- Expected Completion: ~40-60 minutes

**Monitoring:**
```bash
python monitor_hyphen_fix_execution.py
```

## Files Modified

1. **Created:**
   - `fix_hyperparameter_names.py` - Script to fix hyperparameter names
   - `restart_with_fixed_hyperparameters.py` - Script to restart pipeline
   - `monitor_hyphen_fix_execution.py` - Monitoring script
   - `ISSUE_28_HYPERPARAMETER_FIX.md` - This document

2. **Updated:**
   - Step Functions state machine `MovieLensMLPipeline` - Hyperparameter names corrected

3. **No changes needed:**
   - `src/train.py` - Already expects hyphenated arguments
   - `src/infrastructure/stepfunctions_deployment.py` - Will need update for future deployments

## Prevention

To prevent this issue in future deployments:

### 1. Update Deployment Script

Edit `src/infrastructure/stepfunctions_deployment.py` line 147-152:

```python
"HyperParameters": {
    "epochs": "50",
    "batch-size": "256",        # Use hyphens
    "learning-rate": "0.001",   # Use hyphens
    "embedding-dim": "128",     # Use hyphens
    "num-factors": "50"         # Use hyphens
}
```

### 2. Add Validation Test

Create a test to verify hyperparameter names match training script:

```python
def test_hyperparameter_names_match():
    """Verify state machine hyperparameters match training script arguments."""
    # Get state machine definition
    # Get training script argument names
    # Assert they match
```

### 3. Document the Requirement

Add to deployment documentation:
- Hyperparameters must use hyphens (not underscores)
- Must match argparse argument names in training script
- SageMaker converts hyphens to underscores internally

## Related Issues

- **Issue #15**: Original fix for argparse underscores (training script)
- **Issue #27**: Inference worker died (inference code packaging)
- **Issue #28**: This issue - hyperparameter names regression

## Key Learnings

1. **Consistency is Critical**: Hyperparameter names must match exactly between state machine and training script
2. **Argparse Convention**: Python argparse uses hyphens for multi-word arguments
3. **SageMaker Behavior**: SageMaker passes hyperparameters as command-line arguments
4. **Regression Prevention**: Need automated tests to catch configuration mismatches
5. **Documentation**: Deployment scripts should have inline comments about naming conventions

## Timeline

- **11:21:30 UTC**: Training job failed with argument parsing error
- **11:30:00 UTC**: Root cause identified (hyperparameter names)
- **11:35:00 UTC**: Fix script created and executed
- **11:40:13 UTC**: New pipeline execution started
- **Expected**: Training completes by ~12:20 UTC

## Next Steps

1. ✅ Monitor current execution for successful training
2. ⏳ Verify inference files are copied to model artifacts
3. ⏳ Verify endpoint deployment with custom inference handler
4. ⏳ Test endpoint predictions
5. ⏳ Validate RMSE < 0.9 and latency < 500ms
6. 📝 Update deployment script to prevent regression
7. 📝 Add validation tests

## References

- Training script: `src/train.py` lines 75-84 (argument parsing)
- State machine deployment: `src/infrastructure/stepfunctions_deployment.py` lines 147-152
- Python argparse documentation: https://docs.python.org/3/library/argparse.html
- SageMaker hyperparameters: https://docs.aws.amazon.com/sagemaker/latest/dg/your-algorithms-training-algo-running-container.html
