# AWS MovieLens Recommendation System - PowerShell Deployment Script
# This script automates the deployment of the entire system to AWS

# Enable strict mode
$ErrorActionPreference = "Stop"

# Colors for output
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

# Check prerequisites
function Check-Prerequisites {
    Write-Header "Checking Prerequisites"
    
    # Check AWS CLI
    try {
        $awsVersion = aws --version 2>&1
        Write-Success "AWS CLI installed: $awsVersion"
    } catch {
        Write-Error "AWS CLI not found. Please install it first."
        Write-Host "Download from: https://awscli.amazonaws.com/AWSCLIV2.msi"
        exit 1
    }
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Success "Python installed: $pythonVersion"
    } catch {
        Write-Error "Python not found. Please install Python 3.10+."
        exit 1
    }
    
    # Check AWS credentials
    try {
        $identity = aws sts get-caller-identity 2>&1 | ConvertFrom-Json
        Write-Success "AWS credentials configured for account: $($identity.Account)"
    } catch {
        Write-Error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    }
    
    # Check if requirements are installed
    try {
        python -c "import boto3" 2>&1 | Out-Null
        Write-Success "Python dependencies installed"
    } catch {
        Write-Warning "Dependencies not installed. Installing now..."
        pip install -r requirements.txt
    }
}

# Set environment variables
function Setup-Environment {
    Write-Header "Setting Up Environment"
    
    # Get AWS account ID
    $identity = aws sts get-caller-identity | ConvertFrom-Json
    $script:AWS_ACCOUNT_ID = $identity.Account
    
    # Set bucket name (globally unique)
    $script:BUCKET_NAME = "movielens-ml-$AWS_ACCOUNT_ID"
    $script:AWS_REGION = if ($env:AWS_REGION) { $env:AWS_REGION } else { "us-east-1" }
    
    Write-Success "AWS Account ID: $AWS_ACCOUNT_ID"
    Write-Success "S3 Bucket: $BUCKET_NAME"
    Write-Success "Region: $AWS_REGION"
    
    # Confirm with user
    Write-Host ""
    $continue = Read-Host "Continue with these settings? (y/n)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        Write-Error "Deployment cancelled by user"
        exit 1
    }
}

# Download MovieLens dataset
function Download-Dataset {
    Write-Header "Downloading MovieLens Dataset"
    
    if (Test-Path "data\ml-100k") {
        Write-Success "Dataset already downloaded"
        return
    }
    
    New-Item -ItemType Directory -Force -Path "data" | Out-Null
    
    Write-Success "Downloading MovieLens 100K dataset..."
    $url = "https://files.grouplens.org/datasets/movielens/ml-100k.zip"
    $output = "data\ml-100k.zip"
    
    Invoke-WebRequest -Uri $url -OutFile $output
    
    Write-Success "Extracting dataset..."
    Expand-Archive -Path $output -DestinationPath "data" -Force
    Remove-Item $output
    
    Write-Success "Dataset downloaded and extracted"
}

# Upload data to S3
function Upload-Data {
    Write-Header "Uploading Data to S3"
    
    python src\data_upload.py `
        --dataset 100k `
        --bucket $BUCKET_NAME `
        --prefix raw-data/
    
    Write-Success "Data uploaded to S3"
}

# Deploy infrastructure
function Deploy-Infrastructure {
    Write-Header "Deploying AWS Infrastructure"
    
    Write-Success "Creating IAM roles, S3 bucket, Lambda functions, Step Functions..."
    python src\infrastructure\deploy_all.py `
        --bucket-name $BUCKET_NAME `
        --region $AWS_REGION
    
    Write-Success "Infrastructure deployed successfully"
}

# Preprocess data
function Preprocess-Data {
    Write-Header "Preprocessing Data"
    
    python src\preprocessing.py `
        --input-bucket $BUCKET_NAME `
        --input-prefix raw-data/ml-100k/ `
        --output-bucket $BUCKET_NAME `
        --output-prefix processed-data/ `
        --train-ratio 0.8 `
        --val-ratio 0.1
    
    Write-Success "Data preprocessing complete"
}

# Train model
function Train-Model {
    Write-Header "Training Model on SageMaker"
    
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $trainingJobName = "movielens-training-$timestamp"
    
    Write-Success "Starting training job: $trainingJobName"
    Write-Warning "This will take 30-45 minutes..."
    
    python src\infrastructure\sagemaker_deployment.py `
        --bucket-name $BUCKET_NAME `
        --role-name MovieLensSageMakerRole `
        --training-job-name $trainingJobName
    
    Write-Success "Training job started"
    Write-Success "Monitor progress: https://console.aws.amazon.com/sagemaker/home?region=$AWS_REGION#/jobs"
}

# Deploy endpoint
function Deploy-Endpoint {
    Write-Header "Deploying SageMaker Endpoint"
    
    Write-Success "Creating endpoint (this takes 5-10 minutes)..."
    
    python src\infrastructure\sagemaker_deployment.py `
        --bucket-name $BUCKET_NAME `
        --model-name movielens-model `
        --endpoint-name movielens-endpoint `
        --instance-type ml.m5.large `
        --initial-instance-count 1
    
    Write-Success "Endpoint deployment initiated"
}

# Setup auto-scaling
function Setup-AutoScaling {
    Write-Header "Configuring Auto-Scaling"
    
    python src\autoscaling.py `
        --endpoint-name movielens-endpoint `
        --min-capacity 1 `
        --max-capacity 5 `
        --target-invocations 1000
    
    Write-Success "Auto-scaling configured"
}

# Setup monitoring
function Setup-Monitoring {
    Write-Header "Setting Up Monitoring"
    
    python src\monitoring.py `
        --endpoint-name movielens-endpoint `
        --dashboard-name MovieLensMonitoring
    
    Write-Success "CloudWatch dashboard created"
    Write-Success "View at: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:"
}

# Test endpoint
function Test-Endpoint {
    Write-Header "Testing Endpoint"
    
    Write-Success "Running inference test..."
    python src\inference.py `
        --endpoint-name movielens-endpoint `
        --user-id 1 `
        --movie-id 1
    
    Write-Success "Endpoint test successful"
}

# Print summary
function Print-Summary {
    Write-Header "Deployment Complete!"
    
    Write-Host ""
    Write-Host "🎉 Your MovieLens recommendation system is now LIVE on AWS!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Resources Created:" -ForegroundColor Cyan
    Write-Host "  • S3 Bucket: $BUCKET_NAME"
    Write-Host "  • SageMaker Endpoint: movielens-endpoint"
    Write-Host "  • CloudWatch Dashboard: MovieLensMonitoring"
    Write-Host "  • Step Functions: MovieLensMLPipeline"
    Write-Host "  • EventBridge Rule: Weekly retraining (Sundays 2 AM UTC)"
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. View CloudWatch Dashboard:"
    Write-Host "     https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:"
    Write-Host ""
    Write-Host "  2. Test inference:"
    Write-Host "     python src\inference.py --endpoint-name movielens-endpoint --user-id 123 --movie-id 456"
    Write-Host ""
    Write-Host "  3. Monitor costs:"
    Write-Host "     https://console.aws.amazon.com/cost-management/home"
    Write-Host ""
    Write-Host "  4. Review operational procedures:"
    Write-Host "     See RUNBOOK.md for monitoring and troubleshooting"
    Write-Host ""
    Write-Host "Estimated Monthly Cost: `$150-300 USD" -ForegroundColor Yellow
    Write-Host ""
    Write-Warning "Remember to delete resources when done testing to avoid charges!"
    Write-Host "Run: .\cleanup.ps1"
    Write-Host ""
}

# Main deployment flow
function Main {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   AWS MovieLens Recommendation System - Live Deployment   ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Warning "This will deploy resources to AWS and incur costs (~`$150-300/month)"
    $continue = Read-Host "Do you want to continue? (y/n)"
    if ($continue -ne 'y' -and $continue -ne 'Y') {
        Write-Error "Deployment cancelled"
        exit 1
    }
    
    # Run deployment steps
    try {
        Check-Prerequisites
        Setup-Environment
        Download-Dataset
        Upload-Data
        Deploy-Infrastructure
        Preprocess-Data
        Train-Model
        Deploy-Endpoint
        Setup-AutoScaling
        Setup-Monitoring
        Test-Endpoint
        Print-Summary
    } catch {
        Write-Error "Deployment failed: $_"
        Write-Host ""
        Write-Host "Check the error message above and try again."
        Write-Host "For troubleshooting, see RUNBOOK.md"
        exit 1
    }
}

# Run main function
Main
