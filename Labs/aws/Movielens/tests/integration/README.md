# Integration Tests for AWS Infrastructure Deployment

This directory contains integration tests for the MovieLens recommendation system infrastructure deployment.

## Overview

These tests validate the deployment of AWS resources including:
- **S3 bucket creation and configuration** (test_s3_deployment.py)
- **IAM role creation and policies** (test_iam_deployment.py)
- **End-to-end infrastructure deployment** (test_end_to_end_deployment.py)

## Prerequisites

### AWS Credentials

Integration tests require valid AWS credentials with permissions to:
- Create and delete S3 buckets
- Create and delete IAM roles and policies
- Attach and detach IAM policies

Configure credentials using one of these methods:
```bash
# Option 1: AWS CLI configuration
aws configure

# Option 2: Environment variables
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1

# Option 3: AWS credentials file
# ~/.aws/credentials
[default]
aws_access_key_id = your_access_key
aws_secret_access_key = your_secret_key
```

### Test AWS Account

**IMPORTANT**: Use a dedicated test AWS account to avoid affecting production resources.

These tests will create and delete real AWS resources:
- S3 buckets with unique names (test-movielens-{timestamp})
- IAM roles with test prefixes (TestMovieLens{timestamp})

All resources are automatically cleaned up after tests complete.

### Python Dependencies

Install required dependencies:
```bash
pip install -r requirements.txt
```

Required packages:
- boto3
- pytest
- botocore

## Running Tests

### Run All Integration Tests

```bash
# From project root
pytest tests/integration/ -v

# With detailed output
pytest tests/integration/ -v -s
```

### Run Specific Test Files

```bash
# S3 deployment tests only
pytest tests/integration/test_s3_deployment.py -v

# IAM deployment tests only
pytest tests/integration/test_iam_deployment.py -v

# End-to-end deployment tests only
pytest tests/integration/test_end_to_end_deployment.py -v
```

### Run Specific Test Classes

```bash
# Test S3 bucket creation only
pytest tests/integration/test_s3_deployment.py::TestS3BucketCreation -v

# Test IAM role creation only
pytest tests/integration/test_iam_deployment.py::TestIAMRoleCreation -v

# Test end-to-end deployment only
pytest tests/integration/test_end_to_end_deployment.py::TestEndToEndDeployment -v
```

### Run with Coverage

```bash
pytest tests/integration/ --cov=src/infrastructure --cov-report=html
```

## Test Structure

### test_s3_deployment.py

Tests S3 bucket setup functionality:
- **TestS3BucketCreation**: Bucket creation and idempotency
- **TestS3BucketConfiguration**: Versioning, encryption, lifecycle policies, directory structure
- **TestS3BucketPolicy**: Bucket policy configuration
- **TestS3CompleteSetup**: Complete bucket setup workflow

### test_iam_deployment.py

Tests IAM role and policy setup:
- **TestIAMRoleCreation**: Creating SageMaker, Lambda, and Step Functions roles
- **TestIAMRolePolicies**: Verifying attached and inline policies
- **TestIAMRoleTrustPolicies**: Verifying trust relationships
- **TestIAMCompleteSetup**: Complete IAM setup workflow

### test_end_to_end_deployment.py

Tests complete infrastructure deployment:
- **TestEndToEndDeployment**: Full deployment workflow (IAM → S3 → verification)
- **TestDeploymentIdempotency**: Redeployment is idempotent
- **TestDeploymentErrorHandling**: Error handling and graceful failures

## Test Fixtures

### Module-Scoped Fixtures

Tests use module-scoped fixtures to minimize AWS API calls:
- Resources are created once per test module
- Shared across all tests in the module
- Automatically cleaned up after all tests complete

### Cleanup

All test resources are automatically cleaned up using `autouse=True` fixtures:
- S3 buckets: All objects deleted, then bucket deleted
- IAM roles: Policies detached, inline policies deleted, then role deleted

If tests are interrupted, you may need to manually clean up resources:
```bash
# List test buckets
aws s3 ls | grep test-movielens

# Delete test bucket
aws s3 rb s3://test-movielens-{timestamp} --force

# List test roles
aws iam list-roles | grep TestMovieLens

# Delete test role (after detaching policies)
aws iam delete-role --role-name TestMovieLens{timestamp}SageMaker
```

## Expected Test Duration

- **S3 deployment tests**: ~30-60 seconds
- **IAM deployment tests**: ~45-90 seconds
- **End-to-end deployment tests**: ~60-120 seconds
- **Total**: ~2-5 minutes

Duration depends on AWS API response times and network latency.

## Troubleshooting

### Permission Errors

If you see permission errors:
```
ClientError: An error occurred (AccessDenied) when calling the CreateBucket operation
```

Ensure your AWS credentials have the required permissions. Required IAM permissions:
- s3:CreateBucket, s3:DeleteBucket, s3:PutBucketVersioning, etc.
- iam:CreateRole, iam:DeleteRole, iam:AttachRolePolicy, etc.

### Resource Already Exists

If tests fail with "resource already exists" errors:
- Previous test run may not have cleaned up properly
- Manually delete the conflicting resources
- Run tests again

### Rate Limiting

If you see rate limiting errors:
```
ClientError: An error occurred (Throttling) when calling the CreateRole operation
```

AWS has rate limits on API calls. Wait a few minutes and retry.

### Region Issues

Ensure you're using a supported AWS region:
- Default: us-east-1
- Change via AWS_DEFAULT_REGION environment variable

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v1
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v
```

## Best Practices

1. **Use test AWS account**: Never run integration tests in production
2. **Monitor costs**: Integration tests create real AWS resources (minimal cost)
3. **Clean up manually**: If tests fail, check for orphaned resources
4. **Run locally first**: Verify tests pass locally before CI/CD
5. **Parallel execution**: Avoid running tests in parallel (resource conflicts)

## Requirements Validation

These integration tests validate the following requirements:
- **Requirement 1.2**: S3 bucket with organized directory structure
- **Requirement 1.4**: S3 versioning enabled
- **Requirement 1.5**: S3 encryption enabled
- **Requirement 1.6**: S3 lifecycle policies
- **Requirement 12.1**: IAM roles with least-privilege policies
- **Requirement 12.6**: S3 bucket policies for access control

## Support

For issues or questions:
1. Check AWS CloudTrail for detailed error logs
2. Review AWS IAM policy simulator for permission issues
3. Verify AWS service quotas and limits
4. Check test output for specific error messages
