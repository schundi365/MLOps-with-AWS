# Issue #23: Step Functions Missing SageMaker Permissions

## Problem
Execution #22 failed at the CreateModel step with error:
```
User: arn:aws:sts::327030626634:assumed-role/MovieLensStepFunctionsRole/... 
is not authorized to perform: sagemaker:CreateModel on resource: 
arn:aws:sagemaker:us-east-1:327030626634:model/movielens-training-20260122-103324-067 
because no identity-based policy allows the sagemaker:CreateModel action
```

## Root Cause
The MovieLensStepFunctionsRole was missing permissions to:
- `sagemaker:CreateModel`
- `sagemaker:CreateEndpointConfig`
- `sagemaker:CreateEndpoint`

These permissions are required for the deployment workflow:
1. CreateModel - Creates a SageMaker model from training artifacts
2. CreateEndpointConfig - Configures endpoint instance type and count
3. CreateEndpoint - Deploys the model to a real-time inference endpoint

## Solution
Created and executed `fix_stepfunctions_sagemaker_permissions.py` which:

1. Created new IAM policy: `MovieLensStepFunctionsSageMakerPolicy`
2. Added comprehensive SageMaker permissions:
   - CreateModel, DescribeModel, DeleteModel
   - CreateEndpointConfig, DescribeEndpointConfig, DeleteEndpointConfig
   - CreateEndpoint, DescribeEndpoint, DeleteEndpoint, UpdateEndpoint
   - CreateTrainingJob, DescribeTrainingJob, StopTrainingJob
   - CreateProcessingJob, DescribeProcessingJob, StopProcessingJob
   - AddTags, ListTags
3. Attached policy to MovieLensStepFunctionsRole

## Verification
- Policy created: `arn:aws:iam::327030626634:policy/MovieLensStepFunctionsSageMakerPolicy`
- Policy attached to role: MovieLensStepFunctionsRole
- Execution #23 started: 2026-01-22 10:54:37 UTC
- Status: RUNNING (currently in DataPreprocessing step)

## Expected Outcome
Execution #23 should now successfully:
1. Complete preprocessing (~5-10 minutes)
2. Complete training (~60 minutes on ml.m5.xlarge)
3. Deploy model (CreateModel → CreateEndpointConfig → CreateEndpoint)
4. Run evaluation on deployed endpoint
5. Complete successfully

## Files Modified
- Created: `fix_stepfunctions_sagemaker_permissions.py`
- IAM Policy: `MovieLensStepFunctionsSageMakerPolicy` (new)

## Timeline
- Issue discovered: Execution #22 (10:33:26 UTC)
- Fix applied: 10:54:00 UTC
- Execution #23 started: 10:54:37 UTC
- Expected completion: ~12:00 UTC (65-75 minutes total)

## Next Steps
1. Monitor Execution #23 progress
2. Verify deployment step succeeds
3. Verify evaluation step succeeds
4. Run final verification: `python verify_deployment.py`
5. Test predictions: `python test_predictions.py`
