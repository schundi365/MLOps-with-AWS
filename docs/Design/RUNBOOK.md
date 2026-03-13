# Operational Runbook

## Overview

This runbook provides operational procedures for monitoring, troubleshooting, and maintaining the AWS MovieLens Recommendation System. It is intended for DevOps engineers, SREs, and on-call personnel.

## Table of Contents

1. [System Health Monitoring](#system-health-monitoring)
2. [Common Issues and Troubleshooting](#common-issues-and-troubleshooting)
3. [Manual Retraining Procedures](#manual-retraining-procedures)
4. [Endpoint Update Procedures](#endpoint-update-procedures)
5. [Incident Response](#incident-response)
6. [Maintenance Procedures](#maintenance-procedures)
7. [Escalation Procedures](#escalation-procedures)

---

## System Health Monitoring

### Daily Health Checks

Perform these checks daily to ensure system health:

#### 1. Check CloudWatch Dashboard

```bash
# Open CloudWatch Dashboard
aws cloudwatch get-dashboard \
  --dashboard-name MovieLensRecommendationDashboard \
  --region us-east-1
```

**What to Look For**:
- Invocations per minute: Should be within expected range
- Error rate: Should be < 1% (alarm threshold is 5%)
- P99 latency: Should be < 500ms (alarm threshold is 1000ms)
- Instance count: Should match expected traffic patterns

#### 2. Check Endpoint Status

```bash
# List all endpoints
aws sagemaker list-endpoints \
  --name-contains movielens \
  --region us-east-1

# Get endpoint details
aws sagemaker describe-endpoint \
  --endpoint-name movielens-endpoint \
  --region us-east-1
```


**Expected Status**: `InService`

**If Not InService**:
- Check CloudWatch logs for errors
- Review recent deployments
- Check auto-scaling activity

#### 3. Check Active Alarms

```bash
# List active alarms
aws cloudwatch describe-alarms \
  --state-value ALARM \
  --region us-east-1
```

**Action**: Investigate any active alarms immediately.

#### 4. Check Model Monitor Reports

```bash
# List recent monitoring executions
aws sagemaker list-monitoring-executions \
  --monitoring-schedule-name movielens-monitoring \
  --max-results 10 \
  --region us-east-1
```

**What to Look For**:
- Recent execution status: Should be `Completed`
- Violations: Check for data drift or quality issues

#### 5. Check Step Functions Executions

```bash
# List recent executions
aws stepfunctions list-executions \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --max-results 10 \
  --region us-east-1
```

**What to Look For**:
- Recent execution status: Should be `SUCCEEDED`
- Failed executions: Investigate immediately

### Weekly Health Checks

#### 1. Review Cost and Usage

```bash
# Get cost and usage report
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

**Action**: Compare against budget and investigate anomalies.

#### 2. Review S3 Storage

```bash
# Check bucket size
aws s3 ls s3://movielens-recommendation-bucket/ --recursive --summarize
```

**Action**: Verify lifecycle policies are working correctly.

#### 3. Review Training Metrics

Check recent training jobs for performance trends:

```bash
aws sagemaker list-training-jobs \
  --name-contains movielens \
  --max-results 10 \
  --region us-east-1
```

---

## Common Issues and Troubleshooting

### Issue 1: High Error Rate Alarm

**Symptoms**:
- CloudWatch alarm triggered
- Error rate > 5%
- SNS notification received

**Diagnosis Steps**:

1. Check endpoint logs:
```bash
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint --follow
```

2. Check recent invocations:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name ModelInvocation4XXErrors \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 300 \
  --statistics Sum
```


**Common Causes**:
- Invalid input format (4xx errors)
- Model loading failure (5xx errors)
- Instance health issues (5xx errors)
- Timeout issues (5xx errors)

**Resolution**:

For 4xx errors (client issues):
```bash
# Review sample failed requests
aws logs filter-pattern /aws/sagemaker/Endpoints/movielens-endpoint --filter-pattern "4XX"
```
- Contact API consumers to fix input format
- Update API documentation if needed

For 5xx errors (server issues):
```bash
# Check instance health
aws sagemaker describe-endpoint \
  --endpoint-name movielens-endpoint \
  --query 'ProductionVariants[0].CurrentInstanceCount'
```
- If instances are unhealthy, update endpoint to force new instances
- Check model artifacts in S3 are not corrupted
- Review recent deployments for issues

**Escalation**: If error rate remains > 5% after 30 minutes, escalate to ML engineering team.

### Issue 2: High Latency Alarm

**Symptoms**:
- CloudWatch alarm triggered
- P99 latency > 1000ms
- SNS notification received

**Diagnosis Steps**:

1. Check current latency:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name ModelLatency \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 300 \
  --statistics Average,Maximum \
  --extended-statistics p99
```

2. Check instance count and utilization:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name CPUUtilization \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 300 \
  --statistics Average,Maximum
```

**Common Causes**:
- High traffic exceeding capacity
- Auto-scaling not keeping up
- Instance resource exhaustion
- Model inference slowdown

**Resolution**:

For capacity issues:
```bash
# Manually increase instance count
aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name movielens-endpoint \
  --desired-weights-and-capacities VariantName=AllTraffic,DesiredInstanceCount=5
```

For auto-scaling issues:
```bash
# Check auto-scaling policy
aws application-autoscaling describe-scaling-policies \
  --service-namespace sagemaker \
  --resource-id endpoint/movielens-endpoint/variant/AllTraffic
```
- Adjust target value if needed
- Reduce cooldown periods for faster scaling

For instance issues:
- Update endpoint to use larger instance type (ml.m5.2xlarge)
- Check for memory leaks in logs

**Escalation**: If latency remains > 1000ms after scaling, escalate to ML engineering team.

### Issue 3: Endpoint Not Responding

**Symptoms**:
- Endpoint returns 503 Service Unavailable
- All instances showing as unhealthy
- No successful invocations

**Diagnosis Steps**:

1. Check endpoint status:
```bash
aws sagemaker describe-endpoint \
  --endpoint-name movielens-endpoint
```

2. Check recent updates:
```bash
aws sagemaker list-endpoint-configs \
  --name-contains movielens \
  --max-results 5
```

3. Check CloudWatch logs:
```bash
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint --follow
```


**Common Causes**:
- Model artifacts corrupted or missing
- Inference script errors
- Instance launch failures
- IAM permission issues

**Resolution**:

1. Verify model artifacts exist:
```bash
aws s3 ls s3://movielens-recommendation-bucket/models/ --recursive
```

2. If artifacts are missing, retrain model:
```bash
# Trigger retraining pipeline
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --input '{"bucket": "movielens-recommendation-bucket"}'
```

3. If artifacts exist, try redeploying endpoint:
```bash
# Delete and recreate endpoint
aws sagemaker delete-endpoint --endpoint-name movielens-endpoint
python src/infrastructure/sagemaker_deployment.py \
  --model-data s3://movielens-recommendation-bucket/models/model.tar.gz \
  --endpoint-name movielens-endpoint
```

**Escalation**: If endpoint cannot be restored within 1 hour, escalate to ML engineering team.

### Issue 4: Training Job Failed

**Symptoms**:
- Step Functions execution failed
- Training job status: `Failed`
- No model artifacts produced

**Diagnosis Steps**:

1. Get training job details:
```bash
aws sagemaker describe-training-job \
  --training-job-name movielens-training-TIMESTAMP
```

2. Check training logs:
```bash
aws logs tail /aws/sagemaker/TrainingJobs --follow
```

**Common Causes**:
- Out of memory (OOM) errors
- Data format issues
- Hyperparameter configuration errors
- S3 access permission issues

**Resolution**:

For OOM errors:
- Reduce batch_size: 256 → 128
- Reduce embedding_dim: 128 → 64
- Use larger instance type: ml.p3.2xlarge → ml.p3.8xlarge

For data issues:
```bash
# Verify processed data exists
aws s3 ls s3://movielens-recommendation-bucket/processed-data/
```
- If missing, rerun preprocessing job

For permission issues:
```bash
# Check SageMaker execution role
aws iam get-role --role-name SageMakerExecutionRole
```
- Verify role has S3 read/write permissions

**Retry Training**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --input '{
    "bucket": "movielens-recommendation-bucket",
    "embedding_dim": 64,
    "batch_size": 128
  }'
```

### Issue 5: Data Drift Detected

**Symptoms**:
- Model Monitor report shows violations
- Prediction accuracy declining
- Data distribution changes detected

**Diagnosis Steps**:

1. Review monitoring report:
```bash
# Download latest report
aws s3 cp s3://movielens-recommendation-bucket/monitoring/reports/latest/ ./reports/ --recursive
```

2. Check violation details:
```bash
# View constraint violations
cat reports/constraint_violations.json
```

**Common Causes**:
- User behavior changes
- New movies added to catalog
- Seasonal trends
- Data quality issues

**Resolution**:

1. Assess severity of drift
2. If drift is significant (> 20% of features):
   - Trigger immediate retraining
   - Update baseline with recent data

3. Trigger retraining:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --input '{"bucket": "movielens-recommendation-bucket"}'
```

4. Update monitoring baseline:
```bash
python src/monitoring.py \
  --update-baseline \
  --data-path s3://movielens-recommendation-bucket/processed-data/validation.csv
```

---

## Manual Retraining Procedures

### When to Retrain Manually

Trigger manual retraining when:
- Data drift detected (> 20% of features)
- Model accuracy drops below threshold
- New data available (outside weekly schedule)
- After fixing data quality issues
- After hyperparameter tuning experiments


### Standard Retraining Procedure

#### Step 1: Verify Prerequisites

```bash
# Check that raw data is available
aws s3 ls s3://movielens-recommendation-bucket/raw-data/

# Check that infrastructure is healthy
aws sagemaker list-endpoints --name-contains movielens
```

#### Step 2: Trigger Pipeline

```bash
# Start Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --name "manual-retrain-$(date +%Y%m%d-%H%M%S)" \
  --input '{
    "bucket": "movielens-recommendation-bucket",
    "raw_data_prefix": "raw-data/",
    "processed_data_prefix": "processed-data/",
    "model_prefix": "models/",
    "embedding_dim": 128,
    "learning_rate": 0.001,
    "batch_size": 256,
    "epochs": 50
  }'
```

#### Step 3: Monitor Execution

```bash
# Get execution ARN from previous command output
EXECUTION_ARN="arn:aws:states:REGION:ACCOUNT:execution:MovieLensMLPipeline:manual-retrain-TIMESTAMP"

# Check execution status
aws stepfunctions describe-execution \
  --execution-arn $EXECUTION_ARN
```

**Expected Duration**: 30-60 minutes

#### Step 4: Verify Results

After execution completes:

1. Check model artifacts:
```bash
aws s3 ls s3://movielens-recommendation-bucket/models/ --recursive
```

2. Check evaluation metrics:
```bash
aws s3 cp s3://movielens-recommendation-bucket/metrics/evaluation_results.json -
```

3. Verify endpoint updated:
```bash
aws sagemaker describe-endpoint \
  --endpoint-name movielens-endpoint \
  --query 'EndpointStatus'
```

#### Step 5: Validate Endpoint

Test the updated endpoint:

```bash
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name movielens-endpoint \
  --content-type application/json \
  --body '{"user_ids": [1, 2, 3], "movie_ids": [50, 100, 150]}' \
  test_output.json

cat test_output.json
```

**Expected**: Valid predictions returned

### Emergency Retraining (Fast Track)

For urgent retraining needs:

```bash
# Use smaller dataset and fewer epochs
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --name "emergency-retrain-$(date +%Y%m%d-%H%M%S)" \
  --input '{
    "bucket": "movielens-recommendation-bucket",
    "epochs": 20,
    "batch_size": 512
  }'
```

**Expected Duration**: 15-20 minutes

### Rollback Procedure

If new model performs poorly:

1. Identify previous model version:
```bash
aws s3 ls s3://movielens-recommendation-bucket/models/ --recursive | grep model.tar.gz
```

2. Update endpoint to use previous model:
```bash
python src/infrastructure/sagemaker_deployment.py \
  --model-data s3://movielens-recommendation-bucket/models/model-PREVIOUS-VERSION.tar.gz \
  --endpoint-name movielens-endpoint \
  --update
```

3. Verify rollback:
```bash
aws sagemaker describe-endpoint \
  --endpoint-name movielens-endpoint
```

---

## Endpoint Update Procedures

### Updating Model Version

#### Step 1: Prepare New Model

Ensure new model artifacts are in S3:
```bash
aws s3 ls s3://movielens-recommendation-bucket/models/model-NEW-VERSION.tar.gz
```

#### Step 2: Create New Endpoint Configuration

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name movielens-config-$(date +%Y%m%d-%H%M%S) \
  --production-variants \
    VariantName=AllTraffic,\
    ModelName=movielens-model-new,\
    InitialInstanceCount=2,\
    InstanceType=ml.m5.xlarge
```

#### Step 3: Update Endpoint

```bash
aws sagemaker update-endpoint \
  --endpoint-name movielens-endpoint \
  --endpoint-config-name movielens-config-TIMESTAMP
```

**Note**: This performs a blue-green deployment with zero downtime.

#### Step 4: Monitor Update

```bash
# Watch endpoint status
watch -n 10 'aws sagemaker describe-endpoint \
  --endpoint-name movielens-endpoint \
  --query EndpointStatus'
```

**Expected Duration**: 5-10 minutes

#### Step 5: Validate Update

```bash
# Test endpoint
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name movielens-endpoint \
  --content-type application/json \
  --body '{"user_ids": [1], "movie_ids": [50]}' \
  output.json
```


### Scaling Endpoint Instances

#### Increase Instance Count

```bash
# Manually scale up
aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name movielens-endpoint \
  --desired-weights-and-capacities \
    VariantName=AllTraffic,DesiredInstanceCount=5
```

#### Decrease Instance Count

```bash
# Manually scale down
aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name movielens-endpoint \
  --desired-weights-and-capacities \
    VariantName=AllTraffic,DesiredInstanceCount=1
```

**Note**: Auto-scaling will override manual changes based on traffic.

### Changing Instance Type

#### Step 1: Create New Configuration

```bash
aws sagemaker create-endpoint-config \
  --endpoint-config-name movielens-config-larger-$(date +%Y%m%d-%H%M%S) \
  --production-variants \
    VariantName=AllTraffic,\
    ModelName=movielens-model,\
    InitialInstanceCount=2,\
    InstanceType=ml.m5.2xlarge
```

#### Step 2: Update Endpoint

```bash
aws sagemaker update-endpoint \
  --endpoint-name movielens-endpoint \
  --endpoint-config-name movielens-config-larger-TIMESTAMP
```

### Updating Auto-scaling Configuration

```bash
# Update target tracking policy
aws application-autoscaling put-scaling-policy \
  --service-namespace sagemaker \
  --resource-id endpoint/movielens-endpoint/variant/AllTraffic \
  --scalable-dimension sagemaker:variant:DesiredInstanceCount \
  --policy-name movielens-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 100.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance"
    },
    "ScaleOutCooldown": 60,
    "ScaleInCooldown": 300
  }'
```

---

## Incident Response

### Severity Levels

#### P0 - Critical (Response: Immediate)
- Complete system outage
- All endpoints down
- Data loss or corruption
- Security breach

#### P1 - High (Response: < 30 minutes)
- Partial system outage
- Error rate > 10%
- Latency > 2000ms
- Training pipeline failures

#### P2 - Medium (Response: < 2 hours)
- Error rate 5-10%
- Latency 1000-2000ms
- Data drift detected
- Non-critical alarms

#### P3 - Low (Response: < 24 hours)
- Minor performance degradation
- Informational alarms
- Optimization opportunities

### Incident Response Workflow

#### 1. Detection and Alerting

**Automated Alerts**:
- CloudWatch alarms → SNS → Email/SMS
- Model Monitor violations → SNS → Email

**Manual Detection**:
- User reports
- Monitoring dashboard review
- Log analysis

#### 2. Initial Response

1. Acknowledge incident
2. Assess severity level
3. Notify stakeholders
4. Begin investigation

#### 3. Investigation

```bash
# Gather system state
./scripts/gather_diagnostics.sh > incident_$(date +%Y%m%d-%H%M%S).log
```

**Key Information to Collect**:
- Endpoint status and logs
- Recent deployments or changes
- CloudWatch metrics and alarms
- Step Functions execution history
- S3 bucket status

#### 4. Mitigation

Follow troubleshooting procedures for specific issue type.

**Quick Mitigation Options**:
- Scale up instances
- Rollback to previous model
- Disable problematic features
- Route traffic to backup endpoint

#### 5. Resolution

1. Implement permanent fix
2. Verify system stability
3. Update monitoring/alerting
4. Document incident

#### 6. Post-Incident Review

Within 48 hours of resolution:
1. Write incident report
2. Identify root cause
3. Document lessons learned
4. Create action items to prevent recurrence

### Emergency Contacts

| Role | Contact | Escalation Time |
|------|---------|-----------------|
| On-Call Engineer | [Phone/Email] | Immediate |
| ML Engineering Lead | [Phone/Email] | 30 minutes |
| DevOps Manager | [Phone/Email] | 1 hour |
| VP Engineering | [Phone/Email] | 2 hours |

---

## Maintenance Procedures

### Scheduled Maintenance Windows

**Weekly**: Sunday 2:00 AM - 4:00 AM UTC
- Automated retraining
- System updates
- Log rotation

**Monthly**: First Sunday 2:00 AM - 6:00 AM UTC
- Infrastructure updates
- Security patches
- Performance optimization


### Pre-Maintenance Checklist

- [ ] Notify stakeholders 48 hours in advance
- [ ] Backup current model artifacts
- [ ] Verify rollback procedures
- [ ] Prepare maintenance scripts
- [ ] Schedule maintenance window in calendar
- [ ] Set up monitoring for maintenance period

### Post-Maintenance Checklist

- [ ] Verify all services are running
- [ ] Check CloudWatch metrics
- [ ] Test endpoint functionality
- [ ] Review logs for errors
- [ ] Update documentation
- [ ] Notify stakeholders of completion

### Log Rotation

```bash
# Archive old CloudWatch logs
aws logs create-export-task \
  --log-group-name /aws/sagemaker/Endpoints/movielens-endpoint \
  --from 1609459200000 \
  --to 1612137600000 \
  --destination s3://movielens-recommendation-bucket/logs/archive/
```

### Data Cleanup

```bash
# Remove old processed data (> 90 days)
aws s3 rm s3://movielens-recommendation-bucket/processed-data/ \
  --recursive \
  --exclude "*" \
  --include "$(date -d '90 days ago' +%Y%m%d)*"

# Verify lifecycle policies
aws s3api get-bucket-lifecycle-configuration \
  --bucket movielens-recommendation-bucket
```

### Security Updates

#### Update IAM Policies

```bash
# Review and update IAM policies
aws iam get-role-policy \
  --role-name SageMakerExecutionRole \
  --policy-name SageMakerS3Access

# Update policy if needed
aws iam put-role-policy \
  --role-name SageMakerExecutionRole \
  --policy-name SageMakerS3Access \
  --policy-document file://updated-policy.json
```

#### Rotate Access Keys

```bash
# Create new access key
aws iam create-access-key --user-name sagemaker-user

# Update application configuration
# Delete old access key after verification
aws iam delete-access-key \
  --user-name sagemaker-user \
  --access-key-id OLD_KEY_ID
```

#### Update Encryption Keys

```bash
# Rotate KMS keys
aws kms schedule-key-deletion \
  --key-id OLD_KEY_ID \
  --pending-window-in-days 30

# Update S3 bucket encryption
aws s3api put-bucket-encryption \
  --bucket movielens-recommendation-bucket \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "aws:kms",
        "KMSMasterKeyID": "NEW_KEY_ID"
      }
    }]
  }'
```

---

## Escalation Procedures

### When to Escalate

Escalate to next level when:
- Issue not resolved within SLA timeframe
- Issue severity increases
- Multiple systems affected
- Root cause unclear
- Requires specialized expertise

### Escalation Path

```
Level 1: On-Call Engineer (0-30 min)
    ↓ (If unresolved after 30 min)
Level 2: ML Engineering Lead (30-60 min)
    ↓ (If unresolved after 60 min)
Level 3: DevOps Manager (60-120 min)
    ↓ (If unresolved after 120 min)
Level 4: VP Engineering (120+ min)
```

### Escalation Communication Template

```
Subject: [P{SEVERITY}] {BRIEF_DESCRIPTION}

Incident ID: INC-{TIMESTAMP}
Severity: P{0-3}
Start Time: {TIMESTAMP}
Current Status: {STATUS}

Description:
{DETAILED_DESCRIPTION}

Impact:
- Users affected: {NUMBER}
- Services affected: {LIST}
- Business impact: {DESCRIPTION}

Actions Taken:
1. {ACTION_1}
2. {ACTION_2}

Current Blocker:
{BLOCKER_DESCRIPTION}

Requesting:
{SPECIFIC_HELP_NEEDED}
```

---

## Monitoring and Alerting Configuration

### CloudWatch Alarms

#### High Error Rate Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name movielens-high-error-rate \
  --alarm-description "Error rate exceeds 5%" \
  --metric-name Model5XXErrors \
  --namespace AWS/SageMaker \
  --statistic Sum \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --alarm-actions arn:aws:sns:REGION:ACCOUNT:movielens-alerts
```

#### High Latency Alarm

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name movielens-high-latency \
  --alarm-description "P99 latency exceeds 1000ms" \
  --metric-name ModelLatency \
  --namespace AWS/SageMaker \
  --statistic p99 \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 1000 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --alarm-actions arn:aws:sns:REGION:ACCOUNT:movielens-alerts
```

### SNS Topic Configuration

```bash
# Create SNS topic
aws sns create-topic --name movielens-alerts

# Subscribe email
aws sns subscribe \
  --topic-arn arn:aws:sns:REGION:ACCOUNT:movielens-alerts \
  --protocol email \
  --notification-endpoint ops-team@example.com

# Subscribe SMS
aws sns subscribe \
  --topic-arn arn:aws:sns:REGION:ACCOUNT:movielens-alerts \
  --protocol sms \
  --notification-endpoint +1234567890
```

---

## Useful Commands Reference

### Quick Diagnostics

```bash
# System health check
./scripts/health_check.sh

# Get all endpoint metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --metric-name ModelLatency \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```


### Log Analysis

```bash
# Search for errors in last hour
aws logs filter-log-events \
  --log-group-name /aws/sagemaker/Endpoints/movielens-endpoint \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "ERROR"

# Get recent invocations
aws logs filter-log-events \
  --log-group-name /aws/sagemaker/Endpoints/movielens-endpoint \
  --start-time $(date -d '10 minutes ago' +%s)000 \
  --filter-pattern "Invocation"
```

### Performance Analysis

```bash
# Get invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name ModelInvocations \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Get error breakdown
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name Model4XXErrors \
  --dimensions Name=EndpointName,Value=movielens-endpoint \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

### Cost Analysis

```bash
# Get SageMaker costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '30 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon SageMaker"]
    }
  }'

# Get S3 costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '30 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --filter '{
    "Dimensions": {
      "Key": "SERVICE",
      "Values": ["Amazon Simple Storage Service"]
    }
  }'
```

---

## Appendix

### A. Glossary

- **RMSE**: Root Mean Square Error - primary model evaluation metric
- **MAE**: Mean Absolute Error - secondary model evaluation metric
- **P50/P90/P99**: Latency percentiles (50th, 90th, 99th)
- **Blue-Green Deployment**: Zero-downtime deployment strategy
- **Data Drift**: Changes in input data distribution over time
- **Model Monitor**: SageMaker service for detecting drift and quality issues

### B. Related Documentation

- [README.md](README.md) - Setup and installation guide
- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture details
- [Requirements Document](.kiro/specs/aws-movielens-recommendation/requirements.md)
- [Design Document](.kiro/specs/aws-movielens-recommendation/design.md)
- [Tasks Document](.kiro/specs/aws-movielens-recommendation/tasks.md)

### C. External Resources

- [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [AWS CloudWatch Documentation](https://docs.aws.amazon.com/cloudwatch/)
- [AWS Step Functions Documentation](https://docs.aws.amazon.com/step-functions/)
- [MovieLens Dataset](https://grouplens.org/datasets/movielens/)

### D. Change Log

| Date | Version | Changes | Author |
|------|---------|---------|--------|
| 2024-01-14 | 1.0 | Initial runbook creation | System |

### E. Runbook Maintenance

This runbook should be reviewed and updated:
- After each incident
- Quarterly for accuracy
- When system architecture changes
- When new procedures are added

**Last Updated**: 2024-01-14
**Next Review**: 2024-04-14
**Owner**: DevOps Team

---

## Quick Reference Card

### Emergency Procedures

```bash
# Check system health
aws sagemaker describe-endpoint --endpoint-name movielens-endpoint

# View recent errors
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint --follow

# Scale up immediately
aws sagemaker update-endpoint-weights-and-capacities \
  --endpoint-name movielens-endpoint \
  --desired-weights-and-capacities VariantName=AllTraffic,DesiredInstanceCount=5

# Trigger retraining
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:REGION:ACCOUNT:stateMachine:MovieLensMLPipeline \
  --input '{"bucket": "movielens-recommendation-bucket"}'

# Rollback to previous model
python src/infrastructure/sagemaker_deployment.py \
  --model-data s3://movielens-recommendation-bucket/models/model-PREVIOUS.tar.gz \
  --endpoint-name movielens-endpoint --update
```

### Key Metrics Thresholds

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| Error Rate | < 1% | 1-5% | > 5% |
| P99 Latency | < 500ms | 500-1000ms | > 1000ms |
| Instance Count | 1-3 | 3-4 | 5 (max) |
| CPU Utilization | < 60% | 60-80% | > 80% |

### Contact Information

- **On-Call**: [Phone/Pager]
- **ML Team**: [Email/Slack]
- **DevOps**: [Email/Slack]
- **Escalation**: [Phone/Email]

---

**End of Runbook**
