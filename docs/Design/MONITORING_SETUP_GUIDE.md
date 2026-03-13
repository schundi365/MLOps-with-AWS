# Monitoring Setup Guide

## Overview

Your MovieLens recommendation system includes comprehensive monitoring with CloudWatch dashboards and alarms. The monitoring is automatically set up when the pipeline completes.

## What Gets Automatically Created

When the pipeline reaches the "EnableMonitoring" step, the Lambda function creates:

### 1. CloudWatch Dashboard
**Name:** `{endpoint_name}-dashboard`

**Widgets:**
- **Invocations per Minute** - Request volume
- **Model Latency (P50, P90, P99)** - Response times
- **Error Rates (4xx and 5xx)** - Client and server errors
- **CPU Utilization** - Instance CPU usage
- **Memory Utilization** - Instance memory usage

### 2. CloudWatch Alarms

#### High Error Rate Alarm
- **Name:** `{endpoint_name}-high-error-rate`
- **Threshold:** > 5% error rate
- **Evaluation:** 2 consecutive periods of 5 minutes
- **Action:** Sends notification to SNS topic

#### High Latency Alarm
- **Name:** `{endpoint_name}-high-latency`
- **Threshold:** > 1000ms P99 latency (exceeds 500ms requirement)
- **Evaluation:** 2 consecutive periods of 5 minutes
- **Action:** Sends notification to SNS topic

### 3. SNS Topic
**Name:** `MovieLensEndpointAlarms`
**Purpose:** Receives alarm notifications

## Accessing Your Monitoring

### Option 1: AWS Console (Recommended)

#### View Dashboard
1. Go to CloudWatch Console: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1
2. Click "Dashboards" in the left menu
3. Find dashboard: `movielens-endpoint-{timestamp}-dashboard`
4. View real-time metrics

#### View Alarms
1. Go to CloudWatch Console
2. Click "Alarms" → "All alarms"
3. Find alarms:
   - `movielens-endpoint-{timestamp}-high-error-rate`
   - `movielens-endpoint-{timestamp}-high-latency`
4. Check alarm status (OK, ALARM, INSUFFICIENT_DATA)

### Option 2: Using AWS CLI

#### List Dashboards
```bash
aws cloudwatch list-dashboards --region us-east-1
```

#### Get Dashboard
```bash
aws cloudwatch get-dashboard \
  --dashboard-name movielens-endpoint-{timestamp}-dashboard \
  --region us-east-1
```

#### List Alarms
```bash
aws cloudwatch describe-alarms \
  --alarm-name-prefix movielens-endpoint \
  --region us-east-1
```

### Option 3: Using Python Script

I'll create a script for you to check monitoring status.

## Setting Up Email Notifications

To receive email alerts when alarms trigger:

### 1. Subscribe to SNS Topic

```bash
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:{account-id}:MovieLensEndpointAlarms \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-east-1
```

### 2. Confirm Subscription
- Check your email for confirmation message
- Click the confirmation link

### 3. Test Notification (Optional)
```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:{account-id}:MovieLensEndpointAlarms \
  --message "Test notification from MovieLens monitoring" \
  --subject "Test Alert" \
  --region us-east-1
```

## Monitoring Metrics

### Key Metrics to Watch

#### 1. Invocations
- **What:** Number of prediction requests
- **Normal:** Varies based on traffic
- **Alert:** Sudden drops may indicate issues

#### 2. Model Latency
- **P50 (Median):** 50% of requests complete within this time
- **P90:** 90% of requests complete within this time
- **P99:** 99% of requests complete within this time
- **Target:** P99 < 500ms
- **Alert:** P99 > 1000ms triggers alarm

#### 3. Error Rate
- **4xx Errors:** Client errors (bad requests)
- **5xx Errors:** Server errors (model failures)
- **Target:** < 5% combined error rate
- **Alert:** > 5% triggers alarm

#### 4. CPU Utilization
- **Normal:** 20-60% under load
- **High:** > 80% may indicate need for scaling
- **Low:** < 10% may indicate over-provisioning

#### 5. Memory Utilization
- **Normal:** 30-70%
- **High:** > 85% may cause OOM errors
- **Low:** < 20% may indicate over-provisioning

## Customizing Monitoring

### Adjust Alarm Thresholds

If you need different thresholds, you can update alarms:

```python
import boto3

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

# Update latency threshold to 500ms (stricter)
cloudwatch.put_metric_alarm(
    AlarmName='movielens-endpoint-{timestamp}-high-latency',
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2,
    MetricName='ModelLatency',
    Namespace='AWS/SageMaker',
    Period=300,
    Statistic='p99',
    Threshold=500.0,  # Changed from 1000ms to 500ms
    ActionsEnabled=True,
    AlarmActions=['arn:aws:sns:us-east-1:{account-id}:MovieLensEndpointAlarms'],
    Dimensions=[
        {'Name': 'EndpointName', 'Value': 'movielens-endpoint-{timestamp}'},
        {'Name': 'VariantName', 'Value': 'AllTraffic'}
    ]
)
```

### Add Custom Alarms

You can add more alarms for specific needs:

```python
# Example: Alarm for low invocation count (endpoint not being used)
cloudwatch.put_metric_alarm(
    AlarmName='movielens-endpoint-{timestamp}-low-traffic',
    ComparisonOperator='LessThanThreshold',
    EvaluationPeriods=3,
    MetricName='Invocations',
    Namespace='AWS/SageMaker',
    Period=3600,  # 1 hour
    Statistic='Sum',
    Threshold=10.0,  # Less than 10 requests per hour
    ActionsEnabled=True,
    AlarmActions=['arn:aws:sns:us-east-1:{account-id}:MovieLensEndpointAlarms'],
    Dimensions=[
        {'Name': 'EndpointName', 'Value': 'movielens-endpoint-{timestamp}'},
        {'Name': 'VariantName', 'Value': 'AllTraffic'}
    ]
)
```

## Monitoring Best Practices

### 1. Regular Review
- Check dashboard daily during initial deployment
- Review weekly once stable
- Investigate any alarm triggers immediately

### 2. Baseline Establishment
- Monitor for 1-2 weeks to establish normal patterns
- Adjust thresholds based on actual usage
- Document expected ranges for each metric

### 3. Alert Fatigue Prevention
- Set thresholds that indicate real issues
- Use evaluation periods to avoid false alarms
- Adjust as you learn normal behavior

### 4. Incident Response
When an alarm triggers:
1. Check CloudWatch dashboard for context
2. Review CloudWatch Logs for errors
3. Check endpoint status in SageMaker console
4. Investigate recent changes (deployments, traffic patterns)
5. Document the incident and resolution

## Advanced Monitoring

### SageMaker Model Monitor (Optional)

For data drift detection, you can enable SageMaker Model Monitor:

```python
from sagemaker.model_monitor import DataCaptureConfig, DefaultModelMonitor

# Enable data capture
data_capture_config = DataCaptureConfig(
    enable_capture=True,
    sampling_percentage=100,
    destination_s3_uri=f's3://{bucket_name}/model-monitor/data-capture'
)

# Create monitoring schedule
monitor = DefaultModelMonitor(
    role=sagemaker_role,
    instance_count=1,
    instance_type='ml.m5.xlarge',
    volume_size_in_gb=20,
    max_runtime_in_seconds=3600
)

monitor.create_monitoring_schedule(
    monitor_schedule_name='movielens-model-monitor',
    endpoint_input=endpoint_name,
    output_s3_uri=f's3://{bucket_name}/model-monitor/reports',
    statistics=baseline_statistics,
    constraints=baseline_constraints,
    schedule_cron_expression='cron(0 * * * ? *)'  # Hourly
)
```

## Troubleshooting

### Dashboard Not Showing Data
- **Cause:** Endpoint not receiving traffic yet
- **Solution:** Send test predictions, wait 5-10 minutes for metrics

### Alarms Stuck in INSUFFICIENT_DATA
- **Cause:** Not enough data points collected
- **Solution:** Normal for new endpoints, will resolve after traffic

### High Latency Alerts
- **Possible Causes:**
  - Cold start (first request after idle period)
  - Large batch predictions
  - Instance under-provisioned
- **Solutions:**
  - Enable auto-scaling
  - Use larger instance type
  - Implement request batching

### High Error Rate Alerts
- **Possible Causes:**
  - Invalid input format
  - Model inference errors
  - Endpoint capacity exceeded
- **Solutions:**
  - Check CloudWatch Logs for error details
  - Validate input data format
  - Scale up endpoint instances

## Next Steps

1. **Wait for Pipeline Completion** (~40-60 minutes)
2. **Verify Monitoring Setup:**
   ```bash
   python check_monitoring_setup.py
   ```
3. **Subscribe to SNS Topic** for email alerts
4. **Test Endpoint** and verify metrics appear
5. **Review Dashboard** and adjust thresholds if needed

## Quick Reference

### Important ARNs
```
SNS Topic: arn:aws:sns:us-east-1:{account-id}:MovieLensEndpointAlarms
Endpoint: arn:aws:sagemaker:us-east-1:{account-id}:endpoint/movielens-endpoint-{timestamp}
```

### Key Thresholds
- **Error Rate:** > 5% triggers alarm
- **P99 Latency:** > 1000ms triggers alarm
- **Target P99 Latency:** < 500ms (success criteria)

### Useful Commands
```bash
# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name movielens-endpoint-{timestamp}

# View recent logs
aws logs tail /aws/sagemaker/Endpoints/movielens-endpoint-{timestamp} --follow

# List alarms
aws cloudwatch describe-alarms --alarm-name-prefix movielens-endpoint
```

---

**Note:** Replace `{timestamp}` with your actual execution timestamp (e.g., `20260123-122947`)  
**Note:** Replace `{account-id}` with your AWS account ID
