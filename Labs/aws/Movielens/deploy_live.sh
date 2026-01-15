#!/bin/bash

# AWS MovieLens Recommendation System - Live Deployment Script
# This script automates the deployment of the entire system to AWS

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
    echo ""
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        print_error "AWS CLI not found. Please install it first."
        exit 1
    fi
    print_status "AWS CLI installed"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install it first."
        exit 1
    fi
    print_status "Python 3 installed"
    
    # Check AWS credentials
    if ! aws sts get-caller-identity &> /dev/null; then
        print_error "AWS credentials not configured. Run 'aws configure' first."
        exit 1
    fi
    print_status "AWS credentials configured"
    
    # Check if requirements are installed
    if ! python3 -c "import boto3" &> /dev/null; then
        print_warning "Dependencies not installed. Installing now..."
        pip install -r requirements.txt
    fi
    print_status "Python dependencies installed"
}

# Set environment variables
setup_environment() {
    print_header "Setting Up Environment"
    
    # Get AWS account ID
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    
    # Set bucket name (globally unique)
    export BUCKET_NAME="movielens-ml-${AWS_ACCOUNT_ID}"
    export AWS_REGION="${AWS_REGION:-us-east-1}"
    
    print_status "AWS Account ID: $AWS_ACCOUNT_ID"
    print_status "S3 Bucket: $BUCKET_NAME"
    print_status "Region: $AWS_REGION"
    
    # Confirm with user
    echo ""
    read -p "Continue with these settings? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled by user"
        exit 1
    fi
}

# Download MovieLens dataset
download_dataset() {
    print_header "Downloading MovieLens Dataset"
    
    if [ -d "data/ml-100k" ]; then
        print_status "Dataset already downloaded"
        return
    fi
    
    mkdir -p data
    cd data
    
    print_status "Downloading MovieLens 100K dataset..."
    wget -q https://files.grouplens.org/datasets/movielens/ml-100k.zip
    unzip -q ml-100k.zip
    rm ml-100k.zip
    
    cd ..
    print_status "Dataset downloaded and extracted"
}

# Upload data to S3
upload_data() {
    print_header "Uploading Data to S3"
    
    python3 src/data_upload.py \
        --dataset 100k \
        --bucket $BUCKET_NAME \
        --prefix raw-data/
    
    print_status "Data uploaded to S3"
}

# Deploy infrastructure
deploy_infrastructure() {
    print_header "Deploying AWS Infrastructure"
    
    print_status "Creating IAM roles, S3 bucket, Lambda functions, Step Functions..."
    python3 src/infrastructure/deploy_all.py \
        --bucket-name $BUCKET_NAME \
        --region $AWS_REGION
    
    print_status "Infrastructure deployed successfully"
}

# Preprocess data
preprocess_data() {
    print_header "Preprocessing Data"
    
    python3 src/preprocessing.py \
        --input-bucket $BUCKET_NAME \
        --input-prefix raw-data/ml-100k/ \
        --output-bucket $BUCKET_NAME \
        --output-prefix processed-data/ \
        --train-ratio 0.8 \
        --val-ratio 0.1
    
    print_status "Data preprocessing complete"
}

# Train model
train_model() {
    print_header "Training Model on SageMaker"
    
    TRAINING_JOB_NAME="movielens-training-$(date +%Y%m%d-%H%M%S)"
    
    print_status "Starting training job: $TRAINING_JOB_NAME"
    print_warning "This will take 30-45 minutes..."
    
    python3 src/infrastructure/sagemaker_deployment.py \
        --bucket-name $BUCKET_NAME \
        --role-name MovieLensSageMakerRole \
        --training-job-name $TRAINING_JOB_NAME
    
    print_status "Training job started"
    print_status "Monitor progress: https://console.aws.amazon.com/sagemaker/home?region=$AWS_REGION#/jobs"
}

# Deploy endpoint
deploy_endpoint() {
    print_header "Deploying SageMaker Endpoint"
    
    print_status "Creating endpoint (this takes 5-10 minutes)..."
    
    python3 src/infrastructure/sagemaker_deployment.py \
        --bucket-name $BUCKET_NAME \
        --model-name movielens-model \
        --endpoint-name movielens-endpoint \
        --instance-type ml.m5.large \
        --initial-instance-count 1
    
    print_status "Endpoint deployment initiated"
}

# Setup auto-scaling
setup_autoscaling() {
    print_header "Configuring Auto-Scaling"
    
    python3 src/autoscaling.py \
        --endpoint-name movielens-endpoint \
        --min-capacity 1 \
        --max-capacity 5 \
        --target-invocations 1000
    
    print_status "Auto-scaling configured"
}

# Setup monitoring
setup_monitoring() {
    print_header "Setting Up Monitoring"
    
    python3 src/monitoring.py \
        --endpoint-name movielens-endpoint \
        --dashboard-name MovieLensMonitoring
    
    print_status "CloudWatch dashboard created"
    print_status "View at: https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:"
}

# Test endpoint
test_endpoint() {
    print_header "Testing Endpoint"
    
    print_status "Running inference test..."
    python3 src/inference.py \
        --endpoint-name movielens-endpoint \
        --user-id 1 \
        --movie-id 1
    
    print_status "Endpoint test successful"
}

# Print summary
print_summary() {
    print_header "Deployment Complete!"
    
    echo ""
    echo "🎉 Your MovieLens recommendation system is now LIVE on AWS!"
    echo ""
    echo "Resources Created:"
    echo "  • S3 Bucket: $BUCKET_NAME"
    echo "  • SageMaker Endpoint: movielens-endpoint"
    echo "  • CloudWatch Dashboard: MovieLensMonitoring"
    echo "  • Step Functions: MovieLensMLPipeline"
    echo "  • EventBridge Rule: Weekly retraining (Sundays 2 AM UTC)"
    echo ""
    echo "Next Steps:"
    echo "  1. View CloudWatch Dashboard:"
    echo "     https://console.aws.amazon.com/cloudwatch/home?region=$AWS_REGION#dashboards:"
    echo ""
    echo "  2. Test inference:"
    echo "     python3 src/inference.py --endpoint-name movielens-endpoint --user-id 123 --movie-id 456"
    echo ""
    echo "  3. Monitor costs:"
    echo "     https://console.aws.amazon.com/cost-management/home"
    echo ""
    echo "  4. Review operational procedures:"
    echo "     See RUNBOOK.md for monitoring and troubleshooting"
    echo ""
    echo "Estimated Monthly Cost: \$150-300 USD"
    echo ""
    print_warning "Remember to delete resources when done testing to avoid charges!"
    echo "Run: ./cleanup.sh"
    echo ""
}

# Main deployment flow
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   AWS MovieLens Recommendation System - Live Deployment   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_warning "This will deploy resources to AWS and incur costs (~\$150-300/month)"
    read -p "Do you want to continue? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_error "Deployment cancelled"
        exit 1
    fi
    
    # Run deployment steps
    check_prerequisites
    setup_environment
    download_dataset
    upload_data
    deploy_infrastructure
    preprocess_data
    train_model
    deploy_endpoint
    setup_autoscaling
    setup_monitoring
    test_endpoint
    print_summary
}

# Run main function
main
