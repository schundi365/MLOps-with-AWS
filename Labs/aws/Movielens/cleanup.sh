#!/bin/bash

# AWS MovieLens Recommendation System - Cleanup Script
# This script removes all AWS resources to avoid ongoing charges

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Get environment variables
setup_environment() {
    AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    export BUCKET_NAME="movielens-ml-${AWS_ACCOUNT_ID}"
    export AWS_REGION="${AWS_REGION:-us-east-1}"
    
    print_status "AWS Account ID: $AWS_ACCOUNT_ID"
    print_status "S3 Bucket: $BUCKET_NAME"
    print_status "Region: $AWS_REGION"
}

# Delete SageMaker resources
delete_sagemaker() {
    print_header "Deleting SageMaker Resources"
    
    # Delete endpoint
    if aws sagemaker describe-endpoint --endpoint-name movielens-endpoint &> /dev/null; then
        print_status "Deleting SageMaker endpoint..."
        aws sagemaker delete-endpoint --endpoint-name movielens-endpoint
        print_status "Endpoint deleted"
    else
        print_warning "Endpoint not found, skipping"
    fi
    
    # Delete endpoint configuration
    if aws sagemaker describe-endpoint-config --endpoint-config-name movielens-endpoint-config &> /dev/null; then
        print_status "Deleting endpoint configuration..."
        aws sagemaker delete-endpoint-config --endpoint-config-name movielens-endpoint-config
        print_status "Endpoint configuration deleted"
    else
        print_warning "Endpoint configuration not found, skipping"
    fi
    
    # Delete model
    if aws sagemaker describe-model --model-name movielens-model &> /dev/null; then
        print_status "Deleting model..."
        aws sagemaker delete-model --model-name movielens-model
        print_status "Model deleted"
    else
        print_warning "Model not found, skipping"
    fi
}

# Delete S3 bucket
delete_s3() {
    print_header "Deleting S3 Bucket"
    
    if aws s3 ls s3://$BUCKET_NAME &> /dev/null; then
        print_warning "This will delete ALL data in s3://$BUCKET_NAME"
        read -p "Are you sure? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Deleting S3 bucket and all contents..."
            aws s3 rb s3://$BUCKET_NAME --force
            print_status "S3 bucket deleted"
        else
            print_warning "S3 bucket deletion skipped"
        fi
    else
        print_warning "S3 bucket not found, skipping"
    fi
}

# Delete Lambda functions
delete_lambda() {
    print_header "Deleting Lambda Functions"
    
    LAMBDA_FUNCTIONS=("movielens-evaluation" "movielens-monitoring-setup")
    
    for func in "${LAMBDA_FUNCTIONS[@]}"; do
        if aws lambda get-function --function-name $func &> /dev/null; then
            print_status "Deleting Lambda function: $func"
            aws lambda delete-function --function-name $func
        else
            print_warning "Lambda function $func not found, skipping"
        fi
    done
    
    print_status "Lambda functions deleted"
}

# Delete Step Functions
delete_stepfunctions() {
    print_header "Deleting Step Functions"
    
    STATE_MACHINE_ARN="arn:aws:states:$AWS_REGION:$AWS_ACCOUNT_ID:stateMachine:MovieLensMLPipeline"
    
    if aws stepfunctions describe-state-machine --state-machine-arn $STATE_MACHINE_ARN &> /dev/null; then
        print_status "Deleting Step Functions state machine..."
        aws stepfunctions delete-state-machine --state-machine-arn $STATE_MACHINE_ARN
        print_status "State machine deleted"
    else
        print_warning "State machine not found, skipping"
    fi
}

# Delete EventBridge rule
delete_eventbridge() {
    print_header "Deleting EventBridge Rule"
    
    if aws events describe-rule --name MovieLensWeeklyRetraining &> /dev/null; then
        print_status "Removing EventBridge targets..."
        aws events remove-targets --rule MovieLensWeeklyRetraining --ids "1" || true
        
        print_status "Deleting EventBridge rule..."
        aws events delete-rule --name MovieLensWeeklyRetraining
        print_status "EventBridge rule deleted"
    else
        print_warning "EventBridge rule not found, skipping"
    fi
}

# Delete CloudWatch resources
delete_cloudwatch() {
    print_header "Deleting CloudWatch Resources"
    
    # Delete dashboard
    if aws cloudwatch get-dashboard --dashboard-name MovieLensMonitoring &> /dev/null; then
        print_status "Deleting CloudWatch dashboard..."
        aws cloudwatch delete-dashboards --dashboard-names MovieLensMonitoring
        print_status "Dashboard deleted"
    else
        print_warning "Dashboard not found, skipping"
    fi
    
    # Delete alarms
    print_status "Deleting CloudWatch alarms..."
    ALARMS=$(aws cloudwatch describe-alarms --alarm-name-prefix movielens --query 'MetricAlarms[].AlarmName' --output text)
    if [ ! -z "$ALARMS" ]; then
        aws cloudwatch delete-alarms --alarm-names $ALARMS
        print_status "Alarms deleted"
    else
        print_warning "No alarms found, skipping"
    fi
}

# Delete SNS topics
delete_sns() {
    print_header "Deleting SNS Topics"
    
    TOPIC_ARN="arn:aws:sns:$AWS_REGION:$AWS_ACCOUNT_ID:movielens-alerts"
    
    if aws sns get-topic-attributes --topic-arn $TOPIC_ARN &> /dev/null; then
        print_status "Deleting SNS topic..."
        aws sns delete-topic --topic-arn $TOPIC_ARN
        print_status "SNS topic deleted"
    else
        print_warning "SNS topic not found, skipping"
    fi
}

# Delete IAM roles
delete_iam() {
    print_header "Deleting IAM Roles"
    
    print_warning "IAM role deletion requires detaching policies first"
    
    IAM_ROLES=("MovieLensSageMakerRole" "MovieLensLambdaRole" "MovieLensStepFunctionsRole")
    
    for role in "${IAM_ROLES[@]}"; do
        if aws iam get-role --role-name $role &> /dev/null; then
            print_status "Detaching policies from $role..."
            
            # Detach managed policies
            POLICIES=$(aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[].PolicyArn' --output text)
            for policy in $POLICIES; do
                aws iam detach-role-policy --role-name $role --policy-arn $policy
            done
            
            # Delete inline policies
            INLINE_POLICIES=$(aws iam list-role-policies --role-name $role --query 'PolicyNames[]' --output text)
            for policy in $INLINE_POLICIES; do
                aws iam delete-role-policy --role-name $role --policy-name $policy
            done
            
            print_status "Deleting IAM role: $role"
            aws iam delete-role --role-name $role
        else
            print_warning "IAM role $role not found, skipping"
        fi
    done
    
    print_status "IAM roles deleted"
}

# Delete auto-scaling
delete_autoscaling() {
    print_header "Deleting Auto-Scaling Configuration"
    
    RESOURCE_ID="endpoint/movielens-endpoint/variant/AllTraffic"
    
    if aws application-autoscaling describe-scalable-targets \
        --service-namespace sagemaker \
        --resource-ids $RESOURCE_ID &> /dev/null; then
        
        print_status "Deregistering scalable target..."
        aws application-autoscaling deregister-scalable-target \
            --service-namespace sagemaker \
            --resource-id $RESOURCE_ID \
            --scalable-dimension sagemaker:variant:DesiredInstanceCount
        
        print_status "Auto-scaling configuration deleted"
    else
        print_warning "Auto-scaling configuration not found, skipping"
    fi
}

# Print summary
print_summary() {
    print_header "Cleanup Complete!"
    
    echo ""
    echo "✅ All AWS resources have been deleted"
    echo ""
    echo "Deleted Resources:"
    echo "  • SageMaker endpoint and models"
    echo "  • S3 bucket and all data"
    echo "  • Lambda functions"
    echo "  • Step Functions state machine"
    echo "  • EventBridge rules"
    echo "  • CloudWatch dashboards and alarms"
    echo "  • SNS topics"
    echo "  • IAM roles"
    echo "  • Auto-scaling configurations"
    echo ""
    echo "💰 You will no longer be charged for these resources"
    echo ""
    print_warning "Note: It may take a few minutes for all resources to be fully deleted"
    echo ""
}

# Main cleanup flow
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║   AWS MovieLens Recommendation System - Cleanup Script    ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_warning "This will DELETE ALL AWS resources for the MovieLens project"
    print_warning "This action CANNOT be undone!"
    echo ""
    read -p "Are you absolutely sure you want to continue? (yes/no) " -r
    echo ""
    if [[ ! $REPLY == "yes" ]]; then
        print_error "Cleanup cancelled"
        exit 1
    fi
    
    # Setup environment
    setup_environment
    
    # Delete resources in order
    delete_autoscaling
    delete_sagemaker
    delete_stepfunctions
    delete_eventbridge
    delete_lambda
    delete_cloudwatch
    delete_sns
    delete_s3
    delete_iam
    
    print_summary
}

# Run main function
main
