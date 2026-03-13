# Model Health Monitoring Guide

## Overview

The MovieLens recommendation system provides comprehensive monitoring across multiple AWS services. This guide shows you where to find and how to interpret model health metrics.

---

## Quick Access Links

After deployment, access monitoring dashboards here:

| Service | Purpose | AWS Console Link |
|---------|---------|------------------|
| **CloudWatch Dashboard** | Overall system health | [CloudWatch Dashboards](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:) |
| **SageMaker Model Monitor** | Data drift detection | [SageMaker Monitoring](https://console.aws.amazon.com/sagemaker/home?region=us-east-1#/monitoring-schedules) |
| **SageMaker Endpoints** | Inference metrics | [SageMaker Endpoints](https://console.aws.amazon.com/sagemaker/home?region=us-east-1#/endpoints) |
| **Step Functions** | Pipeline execution | [Step Functions](https://console.aws.amazon.com/states/home?region=us-east-1#/statemachines) |
| **CloudWatch Alarms** | Alert status | [CloudWatch Alarms](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:) |

---

## 1. CloudWatch Dashboard - Primary Monitoring Hub

### Access
1. Go to **AWS Console** → **CloudWatch**
2. Click **Dashboards** in left sidebar
3. Find dashboard: `MovieLens-Recommendation-System`

### Key Metrics Displayed

#### Model Performance Metrics
- **Validation RMSE** - Model accuracy (target: < 0.9)
- **Training Loss** - Model convergence over epochs
- **Test RMSE** - Final model quality

#### Endpoint Health Metrics
- **Invocations per Minute** - Request rate
- **Model Latency (P50, P90, P99)** - Response times (target P99: < 500ms)
- **4XX Errors** - Client errors (bad requests)
- **5XX Errors** - Server errors (model failures)

#### Infrastructure Metrics
- **CPU Utilization** - Endpoint compute usage
- **Memory Utilization** - Endpoint memory usage
- **Instance Count** - Auto-scaling status (1-5 instances)

#### Data Quality Metrics
- **Data Drift Score** - Distribution changes in input data
- **Feature Statistics** - Min/max/mean of input features

### How to Read the Dashboard

**🟢 Healthy System:**
- RMSE < 0.9
- P99 latency < 500ms
- 5XX errors = 0
- CPU < 80%

**🟡 Warning Signs:**
- RMSE 0.9-1.0
- P99 latency 500-1000ms
- Occasional 5XX errors
- CPU 80-90%

**🔴 Critical Issues:**
- RMSE > 1.0
- P99 latency > 1000ms
- Frequent 5XX errors
- CPU > 90%

---

## 2. SageMaker Model Monitor - Data Drift Detection

### Access
1. Go to **AWS Console** → **SageMaker**
2. Click **Inference** → **Monitoring schedules**
3. Find: `movielens-endpoint-monitor`

### What It Monitors

#### Data Drift Detection
- **Statistical Distance** - How much input data has changed
- **Feature Distribution** - Changes in user/movie ID distributions
- **Baseline Comparison** - Current data vs. training data

#### Monitoring Schedule
- **Frequency:** Hourly
- **Data Source:** Endpoint data capture (S3)
- **Reports:** Stored in S3 under `monitoring/reports/`

### Interpreting Drift Reports

**View Drift Report:**
1. Click on monitoring schedule
2. Click **View results**
3. Check latest execution

**Drift Indicators:**
- **No Drift:** Distance < 0.1 (green)
- **Minor Drift:** Distance 0.1-0.3 (yellow) - Monitor closely
- **Significant Drift:** Distance > 0.3 (red) - Consider retraining

**Actions on Drift:**
- Minor drift: Continue monitoring
- Significant drift: Trigger manual retraining or wait for weekly schedule

---

## 3. SageMaker Endpoint Metrics - Real-Time Performance

### Access
1. Go to **AWS Console** → **SageMaker**
2. Click **Inference** → **Endpoints**
3. Click on your endpoint (e.g., `movielens-endpoint-prod`)
4. Click **Monitor** tab

### Key Metrics

#### Invocation Metrics
- **Invocations** - Total requests
- **InvocationsPerInstance** - Load per instance
- **ModelLatency** - Time to generate prediction
- **OverheadLatency** - Time for data processing

#### Error Metrics
- **ModelInvocation4XXErrors** - Client errors (bad input)
- **ModelInvocation5XXErrors** - Server errors (model crashes)

#### Instance Metrics
- **CPUUtilization** - Compute usage
- **MemoryUtilization** - Memory usage
- **DiskUtilization** - Storage usage

### Setting Up Alarms

**Create Latency Alarm:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name movielens-high-latency \
  --alarm-description "Alert when P99 latency > 500ms" \
  --metric-name ModelLatency \
  --namespace AWS/SageMaker \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 500 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=EndpointName,Value=movielens-endpoint-prod
```

---

## 4. Step Functions - Pipeline Execution Monitoring

### Access
1. Go to **AWS Console** → **Step Functions**
2. Click on **MovieLensMLPipeline**
3. View execution history

### What to Monitor

#### Execution Status
- **Succeeded** - Pipeline completed successfully
- **Failed** - Pipeline encountered errors
- **Running** - Pipeline currently executing
- **Aborted** - Pipeline manually stopped

#### Execution Timeline
- **Data Preprocessing:** ~5-10 minutes
- **Model Training:** ~30-45 minutes
- **Model Evaluation:** ~2-5 minutes
- **Model Deployment:** ~5-10 minutes
- **Monitoring Setup:** ~1-2 minutes

**Total Pipeline Time:** ~45-75 minutes

### Troubleshooting Failed Executions

**View Error Details:**
1. Click on failed execution
2. Click on failed step (red box)
3. View error message in right panel

**Common Failures:**
- **PreprocessingFailed:** Data format issues
- **TrainingFailed:** Insufficient resources or bad hyperparameters
- **ModelTrainingFailed:** RMSE > 0.9 (quality threshold)
- **DeploymentFailed:** Endpoint creation issues

---

## 5. CloudWatch Logs - Detailed Debugging

### Access
1. Go to **AWS Console** → **CloudWatch**
2. Click **Logs** → **Log groups**

### Key Log Groups

#### SageMaker Training Logs
- **Log Group:** `/aws/sagemaker/TrainingJobs`
- **Contains:** Training progress, loss values, validation metrics
- **Use For:** Debugging training failures

#### SageMaker Endpoint Logs
- **Log Group:** `/aws/sagemaker/Endpoints/movielens-endpoint-prod`
- **Contains:** Inference requests, predictions, errors
- **Use For:** Debugging prediction failures

#### Lambda Function Logs
- **Log Group:** `/aws/lambda/movielens-model-evaluation`
- **Contains:** Model evaluation results, RMSE calculations
- **Use For:** Understanding model quality decisions

#### Step Functions Logs
- **Log Group:** `/aws/states/MovieLensMLPipeline`
- **Contains:** Pipeline execution flow, state transitions
- **Use For:** Debugging pipeline orchestration

### Searching Logs

**Find Errors:**
```
Filter pattern: ERROR
```

**Find High Latency:**
```
Filter pattern: [time, request_id, latency > 500]
```

**Find Specific User:**
```
Filter pattern: "user_id: 123"
```

---

## 6. S3 Monitoring Data - Historical Analysis

### Access
1. Go to **AWS Console** → **S3**
2. Navigate to your bucket: `movielens-ml-327030626634`

### Key Folders

#### `/monitoring/data-capture/`
- **Contains:** Captured inference requests and responses
- **Format:** JSON lines files
- **Retention:** 30 days
- **Use For:** Analyzing prediction patterns

#### `/monitoring/baseline/`
- **Contains:** Baseline statistics from training data
- **Format:** JSON statistics files
- **Use For:** Comparing current data to training data

#### `/monitoring/reports/`
- **Contains:** Hourly drift detection reports
- **Format:** JSON constraint violation reports
- **Use For:** Historical drift analysis

#### `/metrics/`
- **Contains:** Training metrics, evaluation results
- **Format:** JSON metric files
- **Use For:** Model performance history

### Analyzing Captured Data

**Download Recent Predictions:**
```powershell
aws s3 cp s3://movielens-ml-327030626634/monitoring/data-capture/ ./local-data/ --recursive
```

**View Drift Report:**
```powershell
aws s3 cp s3://movielens-ml-327030626634/monitoring/reports/latest.json ./drift-report.json
cat drift-report.json
```

---

## 7. CloudWatch Alarms - Automated Alerts

### Access
1. Go to **AWS Console** → **CloudWatch**
2. Click **Alarms** → **All alarms**

### Recommended Alarms

#### High Latency Alarm
- **Metric:** ModelLatency (P99)
- **Threshold:** > 500ms
- **Action:** SNS notification

#### High Error Rate Alarm
- **Metric:** ModelInvocation5XXErrors
- **Threshold:** > 10 errors in 5 minutes
- **Action:** SNS notification + auto-scaling

#### Low Invocation Rate Alarm
- **Metric:** Invocations
- **Threshold:** < 1 per minute for 30 minutes
- **Action:** SNS notification (possible endpoint issue)

#### Data Drift Alarm
- **Metric:** Custom metric from Model Monitor
- **Threshold:** Drift score > 0.3
- **Action:** SNS notification + trigger retraining

### Setting Up SNS Notifications

**Create SNS Topic:**
```powershell
aws sns create-topic --name movielens-alerts

# Subscribe your email
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:327030626634:movielens-alerts --protocol email --notification-endpoint your-email@example.com
```

---

## 8. Monitoring Best Practices

### Daily Checks (5 minutes)
- [ ] Check CloudWatch Dashboard for anomalies
- [ ] Review endpoint error rate (should be near 0%)
- [ ] Verify auto-scaling is working (1-5 instances)

### Weekly Checks (15 minutes)
- [ ] Review Model Monitor drift reports
- [ ] Check Step Functions execution history
- [ ] Analyze CloudWatch Logs for patterns
- [ ] Review S3 storage costs

### Monthly Checks (30 minutes)
- [ ] Analyze model performance trends
- [ ] Review and optimize CloudWatch alarms
- [ ] Check S3 lifecycle policies
- [ ] Review AWS costs and optimize

### Quarterly Reviews (2 hours)
- [ ] Deep dive into model performance
- [ ] Analyze prediction patterns
- [ ] Review and update monitoring strategy
- [ ] Optimize infrastructure costs

---

## 9. Monitoring CLI Commands

### Quick Health Check
```powershell
# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name movielens-endpoint-prod

# Get recent metrics
aws cloudwatch get-metric-statistics --namespace AWS/SageMaker --metric-name ModelLatency --dimensions Name=EndpointName,Value=movielens-endpoint-prod --start-time 2024-01-01T00:00:00Z --end-time 2024-01-01T23:59:59Z --period 3600 --statistics Average

# Check recent alarms
aws cloudwatch describe-alarms --state-value ALARM
```

### View Recent Logs
```powershell
# Endpoint logs
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint-prod --follow

# Training logs
aws logs tail /aws/sagemaker/TrainingJobs --follow

# Lambda logs
aws logs tail /aws/lambda/movielens-model-evaluation --follow
```

---

## 10. Troubleshooting Common Issues

### Issue: High Latency (P99 > 500ms)

**Diagnosis:**
1. Check CloudWatch Dashboard → Model Latency
2. Check endpoint instance count
3. Check CPU/Memory utilization

**Solutions:**
- Scale up: Increase max instances in auto-scaling
- Scale out: Use larger instance type (ml.m5.xlarge)
- Optimize model: Reduce model complexity

### Issue: High Error Rate (5XX errors)

**Diagnosis:**
1. Check CloudWatch Logs → Endpoint logs
2. Look for error patterns
3. Check model input format

**Solutions:**
- Review input validation
- Check model compatibility
- Redeploy endpoint

### Issue: Data Drift Detected

**Diagnosis:**
1. Check Model Monitor reports
2. Compare current vs. baseline statistics
3. Identify drifting features

**Solutions:**
- Minor drift: Continue monitoring
- Significant drift: Trigger retraining
- Update baseline if drift is expected

### Issue: Training Failures

**Diagnosis:**
1. Check Step Functions execution
2. Review training logs in CloudWatch
3. Check S3 data format

**Solutions:**
- Verify data format
- Adjust hyperparameters
- Increase training resources

---

## Summary

**Primary Monitoring Location:** CloudWatch Dashboard  
**Data Drift Detection:** SageMaker Model Monitor  
**Real-Time Performance:** SageMaker Endpoint Metrics  
**Pipeline Status:** Step Functions Console  
**Detailed Debugging:** CloudWatch Logs  

**Key Metrics to Watch:**
- ✅ RMSE < 0.9
- ✅ P99 Latency < 500ms
- ✅ 5XX Errors = 0
- ✅ Drift Score < 0.3

**Alert Channels:**
- CloudWatch Alarms → SNS → Email
- Step Functions → EventBridge → SNS
- Model Monitor → CloudWatch → SNS

For automated monitoring setup, the system creates all necessary dashboards and alarms during deployment!
