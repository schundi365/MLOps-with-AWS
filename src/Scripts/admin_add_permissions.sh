#!/bin/bash
# Script for AWS Administrator to add monitoring permissions to user 'dev'
# Run this with administrator credentials

echo "=== Adding Monitoring Permissions to User 'dev' ==="
echo ""

# Attach the already-created Step Functions monitoring policy
echo "[1/4] Attaching Step Functions monitoring policy..."
aws iam attach-user-policy \
  --user-name dev \
  --policy-arn arn:aws:iam::327030626634:policy/MovieLensStepFunctionsMonitoring

if [ $? -eq 0 ]; then
    echo "[OK] Step Functions monitoring policy attached"
else
    echo "[X] Failed to attach Step Functions policy"
fi

# Attach AWS managed SageMaker read-only policy
echo ""
echo "[2/4] Attaching SageMaker read-only policy..."
aws iam attach-user-policy \
  --user-name dev \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerReadOnly

if [ $? -eq 0 ]; then
    echo "[OK] SageMaker read-only policy attached"
else
    echo "[X] Failed to attach SageMaker policy"
fi

# Attach CloudWatch Logs read-only policy
echo ""
echo "[3/4] Attaching CloudWatch Logs read-only policy..."
aws iam attach-user-policy \
  --user-name dev \
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess

if [ $? -eq 0 ]; then
    echo "[OK] CloudWatch Logs read-only policy attached"
else
    echo "[X] Failed to attach CloudWatch Logs policy"
fi

# List attached policies to verify
echo ""
echo "[4/4] Verifying attached policies..."
aws iam list-attached-user-policies --user-name dev

echo ""
echo "=== Permissions Added Successfully ==="
echo ""
echo "User 'dev' can now:"
echo "  - Monitor Step Functions executions"
echo "  - View SageMaker training jobs and endpoints"
echo "  - Read CloudWatch logs"
echo ""
echo "User should wait 10-15 seconds for permissions to propagate,"
echo "then run: python monitor_pipeline.py"
