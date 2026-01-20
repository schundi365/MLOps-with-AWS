# Required IAM Permissions for Pipeline Monitoring

## Current Situation

Your IAM user (`dev`) has successfully deployed the infrastructure but lacks permissions to monitor it. The following permissions are needed:

## Required Permissions

### 1. Step Functions (Pipeline Orchestration)
```json
{
    "Effect": "Allow",
    "Action": [
        "states:ListStateMachines",
        "states:ListExecutions",
        "states:DescribeStateMachine",
        "states:DescribeExecution",
        "states:GetExecutionHistory",
        "states:StartExecution"
    ],
    "Resource": "*"
}
```

### 2. SageMaker (Training & Endpoints)
```json
{
    "Effect": "Allow",
    "Action": [
        "sagemaker:ListTrainingJobs",
        "sagemaker:DescribeTrainingJob",
        "sagemaker:ListEndpoints",
        "sagemaker:DescribeEndpoint",
        "sagemaker:ListEndpointConfigs",
        "sagemaker:DescribeEndpointConfig",
        "sagemaker:ListModels",
        "sagemaker:DescribeModel"
    ],
    "Resource": "*"
}
```

### 3. CloudWatch Logs (Debugging)
```json
{
    "Effect": "Allow",
    "Action": [
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:GetLogEvents",
        "logs:FilterLogEvents"
    ],
    "Resource": "*"
}
```

### 4. IAM (Self-Service Permissions)
```json
{
    "Effect": "Allow",
    "Action": [
        "iam:AttachUserPolicy",
        "iam:DetachUserPolicy",
        "iam:ListAttachedUserPolicies"
    ],
    "Resource": "arn:aws:iam::327030626634:user/dev"
}
```

## Policy Already Created

A policy named `MovieLensStepFunctionsMonitoring` has been created with ARN:
```
arn:aws:iam::327030626634:policy/MovieLensStepFunctionsMonitoring
```

This policy includes Step Functions and CloudWatch Logs permissions.

## What Your Administrator Needs to Do

### Option 1: Attach the Existing Policy (Quick)

Run this AWS CLI command:

```bash
aws iam attach-user-policy \
  --user-name dev \
  --policy-arn arn:aws:iam::327030626634:policy/MovieLensStepFunctionsMonitoring
```

### Option 2: Create Complete Monitoring Policy (Recommended)

1. Go to IAM Console: https://console.aws.amazon.com/iam/
2. Click "Policies" → "Create policy"
3. Click "JSON" tab
4. Paste the complete policy below
5. Name it: `MovieLensCompleteMonitoring`
6. Attach it to user `dev`

**Complete Policy JSON**:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "StepFunctionsMonitoring",
            "Effect": "Allow",
            "Action": [
                "states:ListStateMachines",
                "states:ListExecutions",
                "states:DescribeStateMachine",
                "states:DescribeExecution",
                "states:GetExecutionHistory",
                "states:StartExecution"
            ],
            "Resource": "*"
        },
        {
            "Sid": "SageMakerMonitoring",
            "Effect": "Allow",
            "Action": [
                "sagemaker:ListTrainingJobs",
                "sagemaker:DescribeTrainingJob",
                "sagemaker:ListEndpoints",
                "sagemaker:DescribeEndpoint",
                "sagemaker:ListEndpointConfigs",
                "sagemaker:DescribeEndpointConfig",
                "sagemaker:ListModels",
                "sagemaker:DescribeModel"
            ],
            "Resource": "*"
        },
        {
            "Sid": "CloudWatchLogsRead",
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:GetLogEvents",
                "logs:FilterLogEvents"
            ],
            "Resource": "*"
        },
        {
            "Sid": "SelfServiceIAM",
            "Effect": "Allow",
            "Action": [
                "iam:AttachUserPolicy",
                "iam:DetachUserPolicy",
                "iam:ListAttachedUserPolicies"
            ],
            "Resource": "arn:aws:iam::327030626634:user/dev"
        }
    ]
}
```

### Option 3: Use AWS Managed Policies (Easiest)

Attach these AWS managed policies to user `dev`:

1. **ReadOnlyAccess** (gives read access to all AWS services)
   - ARN: `arn:aws:iam::aws:policy/ReadOnlyAccess`
   - Command: `aws iam attach-user-policy --user-name dev --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess`

**OR** (more restrictive):

2. **AWSStepFunctionsReadOnlyAccess**
   - ARN: `arn:aws:iam::aws:policy/AWSStepFunctionsReadOnlyAccess`

3. **AmazonSageMakerReadOnly**
   - ARN: `arn:aws:iam::aws:policy/AmazonSageMakerReadOnly`

4. **CloudWatchLogsReadOnlyAccess**
   - ARN: `arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess`

## Current Pipeline Status

Based on S3 check:
- ✅ Data uploaded to `raw-data/` (4 files at 15:20:03)
- ⏳ Pipeline is running (preprocessing stage)
- ⏳ Waiting for processed data to appear

## Workaround: Use AWS Console

Until permissions are added, monitor via AWS Console:

### Step Functions Console
https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines/view/arn:aws:states:us-east-1:327030626634:stateMachine:MovieLensMLPipeline

**Current Execution**:
- Execution ID: `execution-20260119-152014`
- Started: 15:20:14 UTC
- Expected duration: 30-60 minutes

### What to Look For:

1. **Green checkmarks** = Steps completed successfully
2. **Blue/spinning** = Currently running
3. **Red X** = Failed (check logs)

### Pipeline Steps:
1. ✅ Start
2. ⏳ Preprocessing (current - should take 5-10 min)
3. ⏳ Training (15-30 min)
4. ⏳ Evaluation (2-5 min)
5. ⏳ Deployment (5-10 min)
6. ⏳ Monitoring Setup (2-3 min)

## After Permissions Are Added

Run these commands to verify:

```powershell
# Check if permissions work
python check_pipeline_simple.py

# Monitor in real-time
python monitor_pipeline.py

# Full status check
python check_deployment_status.py
```

## Contact Your Administrator

Send them this file and ask them to:
1. Attach the `MovieLensStepFunctionsMonitoring` policy (already created)
2. Add SageMaker read permissions
3. Or attach AWS managed `ReadOnlyAccess` policy

**Policy ARN to attach**: `arn:aws:iam::327030626634:policy/MovieLensStepFunctionsMonitoring`
**User**: `dev`
**Account**: `327030626634`
