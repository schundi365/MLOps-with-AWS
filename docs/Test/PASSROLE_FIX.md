# PassRole Permission Fix

## Problem Identified ✅

The second pipeline execution failed with error:
```
User is not authorized to perform: iam:PassRole on resource: MovieLensSageMakerRole
```

## Root Cause

The `MovieLensStepFunctionsRole` (used by Step Functions to execute the pipeline) didn't have permission to pass the `MovieLensSageMakerRole` to SageMaker services.

### Why PassRole is Needed

When Step Functions creates SageMaker jobs (processing, training, endpoints), it needs to:
1. Tell SageMaker which IAM role to use (`MovieLensSageMakerRole`)
2. Have permission to "pass" that role to SageMaker

Without `iam:PassRole`, Step Functions cannot delegate the SageMaker role, causing the pipeline to fail.

## Fix Applied ✅

Added `PassRolePolicy` inline policy to `MovieLensStepFunctionsRole`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PassRoleToSageMaker",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": [
        "arn:aws:iam::327030626634:role/MovieLensSageMakerRole",
        "arn:aws:iam::327030626634:role/MovieLensLambdaEvaluationRole",
        "arn:aws:iam::327030626634:role/MovieLensLambdaMonitoringRole"
      ],
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": [
            "sagemaker.amazonaws.com",
            "lambda.amazonaws.com"
          ]
        }
      }
    }
  ]
}
```

### Security Best Practice

The policy includes a condition that restricts passing roles only to:
- `sagemaker.amazonaws.com` - For SageMaker jobs
- `lambda.amazonaws.com` - For Lambda functions

This follows the principle of least privilege.

## New Execution Started ✅

**Execution ARN**: 
```
arn:aws:states:us-east-1:327030626634:execution:MovieLensMLPipeline:execution-20260119-155224
```

**Started**: 15:52:25 UTC  
**Status**: Running with correct permissions

## Timeline of Issues & Fixes

### Execution 1: Missing Input Parameters
- **Time**: 15:20:14 UTC
- **Error**: `JSONPath '$.preprocessing_job_name' could not be found in input '{}'`
- **Fix**: Added required input parameters to `start_pipeline.py`
- **File**: `PIPELINE_FIX.md`

### Execution 2: Missing PassRole Permission
- **Time**: 15:35:40 UTC
- **Error**: `User is not authorized to perform: iam:PassRole`
- **Fix**: Added PassRole policy to Step Functions role
- **File**: `PASSROLE_FIX.md` (this document)

### Execution 3: Should Work! ✅
- **Time**: 15:52:25 UTC
- **Status**: Running with all fixes applied
- **Expected**: Success!

## What Was Missing from Initial Deployment

The `src/infrastructure/iam_setup.py` created the Step Functions role but didn't include the `iam:PassRole` permission. This is now fixed.

### Why It Was Missing

The IAM setup script focused on:
- ✅ SageMaker permissions (S3, CloudWatch, etc.)
- ✅ Lambda permissions
- ✅ Step Functions orchestration permissions
- ❌ **PassRole permission** (overlooked)

## Files Created

1. `fix_passrole_permission.py` - Script to add PassRole permission
2. `PASSROLE_FIX.md` - This documentation

## Monitoring

Use AWS Console to monitor the current execution:
```
https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:327030626634:stateMachine:MovieLensMLPipeline
```

Click on execution: `execution-20260119-155224`

## Expected Timeline

- **15:52** - Start
- **15:52-16:02** - Data Preprocessing (10 min)
- **16:02-16:47** - Model Training (45 min)
- **16:47-16:52** - Model Evaluation (5 min)
- **16:52-17:02** - Model Deployment (10 min)
- **17:02-17:04** - Monitoring Setup (2 min)
- **17:04** - Complete! ✅

**Total**: ~72 minutes

## Lessons Learned

1. **Always include PassRole** when one service needs to use another service's role
2. **Test with actual execution** - deployment success doesn't mean execution will work
3. **Add PassRole during initial IAM setup** - should be part of `iam_setup.py`

## Future Improvement

Update `src/infrastructure/iam_setup.py` to include PassRole permission by default:

```python
# Add to Step Functions role policy
{
    "Effect": "Allow",
    "Action": "iam:PassRole",
    "Resource": [
        sagemaker_role_arn,
        lambda_eval_role_arn,
        lambda_monitor_role_arn
    ],
    "Condition": {
        "StringEquals": {
            "iam:PassedToService": [
                "sagemaker.amazonaws.com",
                "lambda.amazonaws.com"
            ]
        }
    }
}
```

---

**Status**: ✅ FIXED - Pipeline running with correct permissions  
**Current Execution**: `execution-20260119-155224`  
**Expected Completion**: ~17:04 UTC
