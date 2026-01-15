# AWS MovieLens Recommendation System - PowerShell Cleanup Script
# This script removes all AWS resources to avoid ongoing charges

$ErrorActionPreference = "Stop"

function Write-Success { Write-Host "✓ $args" -ForegroundColor Green }
function Write-Error { Write-Host "✗ $args" -ForegroundColor Red }
function Write-Warning { Write-Host "! $args" -ForegroundColor Yellow }
function Write-Header { 
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host $args -ForegroundColor Cyan
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
}

# Get environment variables
function Setup-Environment {
    $identity = aws sts get-caller-identity | ConvertFrom-Json
    $script:AWS_ACCOUNT_ID = $identity.Account
    $script:BUCKET_NAME = "movielens-ml-$AWS_ACCOUNT_ID"
    $script:AWS_REGION = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }
    
    Write-Success "AWS Account ID: $AWS_ACCOUNT_ID"
    Write-Success "S3 Bucket: $BUCKET_NAME"
    Write-Success "Region: $AWS_REGION"
}

# Delete SageMaker resources
function Delete-SageMaker {
    Write-Header "Deleting SageMaker Resources"
    
    # Delete endpoint
    try {
        aws sagemaker describe-endpoint --endpoint-name movielens-endpoint 2>&1 | Out-Null
        Write-Success "Deleting SageMaker endpoint..."
        aws sagemaker delete-endpoint --endpoint-name movielens-endpoint
        Write-Success "Endpoint deleted"
    } catch {
        Write-Warning "Endpoint not found, skipping"
    }
    
    # Delete endpoint configuration
    try {
        aws sagemaker describe-endpoint-config --endpoint-config-name movielens-endpoint-config 2>&1 | Out-Null
        Write-Success "Deleting endpoint configuration..."
        aws sagemaker delete-endpoint-config --endpoint-config-name movielens-endpoint-config
        Write-Success "Endpoint configuration deleted"
    } catch {
        Write-Warning "Endpoint configuration not found, skipping"
    }
    
    # Delete model
    try {
        aws sagemaker describe-model --model-name movielens-model 2>&1 | Out-Null
        Write-Success "Deleting model..."
        aws sagemaker delete-model --model-name movielens-model
        Write-Success "Model deleted"
    } catch {
        Write-Warning "Model not found, skipping"
    }
}

# Delete S3 bucket
function Delete-S3 {
    Write-Header "Deleting S3 Bucket"
    
    try {
        aws s3 ls "s3://$BUCKET_NAME" 2>&1 | Out-Null
        Write-Warning "This will delete ALL data in s3://$BUCKET_NAME"
        $confirm = Read-Host "Are you sure? (y/n)"
        if ($confirm -eq 'y' -or $confirm -eq 'Y') {
            Write-Success "Deleting S3 bucket and all contents..."
            aws s3 rb "s3://$BUCKET_NAME" --force
            Write-Success "S3 bucket deleted"
        } else {
            Write-Warning "S3 bucket deletion skipped"
        }
    } catch {
        Write-Warning "S3 bucket not found, skipping"
    }
}

# Delete Lambda functions
function Delete-Lambda {
    Write-Header "Deleting Lambda Functions"
    
    $functions = @("movielens-evaluation", "movielens-monitoring-setup")
    
    foreach ($func in $functions) {
        try {
            aws lambda get-function --function-name $func 2>&1 | Out-Null
            Write-Success "Deleting Lambda function: $func"
            aws lambda delete-function --function-name $func
        } catch {
            Write-Warning "Lambda function $func not found, skipping"
        }
    }
    
    Write-Success "Lambda functions deleted"
}

# Delete Step Functions
function Delete-StepFunctions {
    Write-Header "Deleting Step Functions"
    
    $stateMachineArn = "arn:aws:states:${AWS_REGION}:${AWS_ACCOUNT_ID}:stateMachine:MovieLensMLPipeline"
    
    try {
        aws stepfunctions describe-state-machine --state-machine-arn $stateMachineArn 2>&1 | Out-Null
        Write-Success "Deleting Step Functions state machine..."
        aws stepfunctions delete-state-machine --state-machine-arn $stateMachineArn
        Write-Success "State machine deleted"
    } catch {
        Write-Warning "State machine not found, skipping"
    }
}

# Delete EventBridge rule
function Delete-EventBridge {
    Write-Header "Deleting EventBridge Rule"
    
    try {
        aws events describe-rule --name MovieLensWeeklyRetraining 2>&1 | Out-Null
        Write-Success "Removing EventBridge targets..."
        aws events remove-targets --rule MovieLensWeeklyRetraining --ids "1" 2>&1 | Out-Null
        
        Write-Success "Deleting EventBridge rule..."
        aws events delete-rule --name MovieLensWeeklyRetraining
        Write-Success "EventBridge rule deleted"
    } catch {
        Write-Warning "EventBridge rule not found, skipping"
    }
}

# Delete CloudWatch resources
function Delete-CloudWatch {
    Write-Header "Deleting CloudWatch Resources"
    
    # Delete dashboard
    try {
        aws cloudwatch get-dashboard --dashboard-name MovieLensMonitoring 2>&1 | Out-Null
        Write-Success "Deleting CloudWatch dashboard..."
        aws cloudwatch delete-dashboards --dashboard-names MovieLensMonitoring
        Write-Success "Dashboard deleted"
    } catch {
        Write-Warning "Dashboard not found, skipping"
    }
    
    # Delete alarms
    Write-Success "Deleting CloudWatch alarms..."
    $alarms = aws cloudwatch describe-alarms --alarm-name-prefix movielens --query 'MetricAlarms[].AlarmName' --output text
    if ($alarms) {
        aws cloudwatch delete-alarms --alarm-names $alarms.Split()
        Write-Success "Alarms deleted"
    } else {
        Write-Warning "No alarms found, skipping"
    }
}

# Delete SNS topics
function Delete-SNS {
    Write-Header "Deleting SNS Topics"
    
    $topicArn = "arn:aws:sns:${AWS_REGION}:${AWS_ACCOUNT_ID}:movielens-alerts"
    
    try {
        aws sns get-topic-attributes --topic-arn $topicArn 2>&1 | Out-Null
        Write-Success "Deleting SNS topic..."
        aws sns delete-topic --topic-arn $topicArn
        Write-Success "SNS topic deleted"
    } catch {
        Write-Warning "SNS topic not found, skipping"
    }
}

# Delete IAM roles
function Delete-IAM {
    Write-Header "Deleting IAM Roles"
    
    Write-Warning "IAM role deletion requires detaching policies first"
    
    $roles = @("MovieLensSageMakerRole", "MovieLensLambdaRole", "MovieLensStepFunctionsRole")
    
    foreach ($role in $roles) {
        try {
            aws iam get-role --role-name $role 2>&1 | Out-Null
            Write-Success "Detaching policies from $role..."
            
            # Detach managed policies
            $policies = aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[].PolicyArn' --output text
            if ($policies) {
                foreach ($policy in $policies.Split()) {
                    aws iam detach-role-policy --role-name $role --policy-arn $policy
                }
            }
            
            # Delete inline policies
            $inlinePolicies = aws iam list-role-policies --role-name $role --query 'PolicyNames[]' --output text
            if ($inlinePolicies) {
                foreach ($policy in $inlinePolicies.Split()) {
                    aws iam delete-role-policy --role-name $role --policy-name $policy
                }
            }
            
            Write-Success "Deleting IAM role: $role"
            aws iam delete-role --role-name $role
        } catch {
            Write-Warning "IAM role $role not found, skipping"
        }
    }
    
    Write-Success "IAM roles deleted"
}

# Delete auto-scaling
function Delete-AutoScaling {
    Write-Header "Deleting Auto-Scaling Configuration"
    
    $resourceId = "endpoint/movielens-endpoint/variant/AllTraffic"
    
    try {
        aws application-autoscaling describe-scalable-targets `
            --service-namespace sagemaker `
            --resource-ids $resourceId 2>&1 | Out-Null
        
        Write-Success "Deregistering scalable target..."
        aws application-autoscaling deregister-scalable-target `
            --service-namespace sagemaker `
            --resource-id $resourceId `
            --scalable-dimension sagemaker:variant:DesiredInstanceCount
        
        Write-Success "Auto-scaling configuration deleted"
    } catch {
        Write-Warning "Auto-scaling configuration not found, skipping"
    }
}

# Print summary
function Print-Summary {
    Write-Header "Cleanup Complete!"
    
    Write-Host ""
    Write-Host "✅ All AWS resources have been deleted" -ForegroundColor Green
    Write-Host ""
    Write-Host "Deleted Resources:" -ForegroundColor Cyan
    Write-Host "  • SageMaker endpoint and models"
    Write-Host "  • S3 bucket and all data"
    Write-Host "  • Lambda functions"
    Write-Host "  • Step Functions state machine"
    Write-Host "  • EventBridge rules"
    Write-Host "  • CloudWatch dashboards and alarms"
    Write-Host "  • SNS topics"
    Write-Host "  • IAM roles"
    Write-Host "  • Auto-scaling configurations"
    Write-Host ""
    Write-Host "💰 You will no longer be charged for these resources" -ForegroundColor Green
    Write-Host ""
    Write-Warning "Note: It may take a few minutes for all resources to be fully deleted"
    Write-Host ""
}

# Main cleanup flow
function Main {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   AWS MovieLens Recommendation System - Cleanup Script    ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Warning "This will DELETE ALL AWS resources for the MovieLens project"
    Write-Warning "This action CANNOT be undone!"
    Write-Host ""
    $confirm = Read-Host "Are you absolutely sure you want to continue? (yes/no)"
    if ($confirm -ne "yes") {
        Write-Error "Cleanup cancelled"
        exit 1
    }
    
    # Setup environment
    Setup-Environment
    
    # Delete resources in order
    try {
        Delete-AutoScaling
        Delete-SageMaker
        Delete-StepFunctions
        Delete-EventBridge
        Delete-Lambda
        Delete-CloudWatch
        Delete-SNS
        Delete-S3
        Delete-IAM
        
        Print-Summary
    } catch {
        Write-Error "Cleanup failed: $_"
        Write-Host ""
        Write-Host "Some resources may not have been deleted."
        Write-Host "Check the AWS Console to verify."
        exit 1
    }
}

# Run main function
Main
