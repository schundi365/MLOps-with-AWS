# PowerShell script for AWS Administrator to add monitoring permissions to user 'dev'
# Run this with administrator credentials

Write-Host "`n=== Adding Monitoring Permissions to User 'dev' ===`n" -ForegroundColor Cyan

# Attach the already-created Step Functions monitoring policy
Write-Host "[1/4] Attaching Step Functions monitoring policy..." -ForegroundColor Yellow
aws iam attach-user-policy `
  --user-name dev `
  --policy-arn arn:aws:iam::327030626634:policy/MovieLensStepFunctionsMonitoring

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Step Functions monitoring policy attached" -ForegroundColor Green
} else {
    Write-Host "[X] Failed to attach Step Functions policy" -ForegroundColor Red
}

# Attach AWS managed SageMaker read-only policy
Write-Host "`n[2/4] Attaching SageMaker read-only policy..." -ForegroundColor Yellow
aws iam attach-user-policy `
  --user-name dev `
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerReadOnly

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] SageMaker read-only policy attached" -ForegroundColor Green
} else {
    Write-Host "[X] Failed to attach SageMaker policy" -ForegroundColor Red
}

# Attach CloudWatch Logs read-only policy
Write-Host "`n[3/4] Attaching CloudWatch Logs read-only policy..." -ForegroundColor Yellow
aws iam attach-user-policy `
  --user-name dev `
  --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsReadOnlyAccess

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] CloudWatch Logs read-only policy attached" -ForegroundColor Green
} else {
    Write-Host "[X] Failed to attach CloudWatch Logs policy" -ForegroundColor Red
}

# List attached policies to verify
Write-Host "`n[4/4] Verifying attached policies..." -ForegroundColor Yellow
aws iam list-attached-user-policies --user-name dev

Write-Host "`n=== Permissions Added Successfully ===" -ForegroundColor Green
Write-Host "`nUser 'dev' can now:" -ForegroundColor Cyan
Write-Host "  - Monitor Step Functions executions"
Write-Host "  - View SageMaker training jobs and endpoints"
Write-Host "  - Read CloudWatch logs"
Write-Host "`nUser should wait 10-15 seconds for permissions to propagate," -ForegroundColor Yellow
Write-Host "then run: python monitor_pipeline.py`n"
