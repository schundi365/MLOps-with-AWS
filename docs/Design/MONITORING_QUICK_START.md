# Monitoring Quick Start Guide

## 🎯 Your System is Live!

**Endpoint:** `movielens-endpoint-20260123-122948`  
**Status:** ✅ InService and ready for predictions

---

## 3 Steps to Complete Setup

### Step 1: Test Your Endpoint (2 minutes)

```bash
python test_endpoint_predictions.py
```

This will:
- Send 10 test predictions
- Show predicted ratings
- Measure latency
- Calculate error rates

**Expected:** All tests pass with latency < 500ms

---

### Step 2: Subscribe to Email Alerts (3 minutes)

1. Open SNS Console:
   ```
   https://console.aws.amazon.com/sns/v3/home?region=us-east-1#/topics
   ```

2. Click on topic: **MovieLensEndpointAlarms**

3. Click **"Create subscription"**

4. Fill in:
   - Protocol: **Email**
   - Endpoint: **your-email@example.com**

5. Click **"Create subscription"**

6. **Check your email** and click confirmation link

**You'll receive alerts when:**
- Error rate exceeds 5%
- P99 latency exceeds 1000ms

---

### Step 3: View Your Dashboard (1 minute)

1. Open CloudWatch Console:
   ```
   https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:
   ```

2. Click on dashboard: **movielens-endpoint-20260123-122948-dashboard**

3. View real-time metrics:
   - 📊 Invocations per minute
   - ⏱️ Latency (P50, P90, P99)
   - ❌ Error rates
   - 💻 CPU utilization
   - 🧠 Memory utilization

**Note:** Metrics appear 5-10 minutes after sending requests

---

## What You Get

### Automatic Monitoring ✅

Your system automatically tracks:
- **Request Volume:** How many predictions per minute
- **Response Time:** P50, P90, P99 latency
- **Error Rates:** 4xx (client) and 5xx (server) errors
- **Resource Usage:** CPU and memory utilization

### Automatic Alerts ✅

You'll receive email alerts when:
- **High Error Rate:** > 5% of requests fail
- **High Latency:** P99 latency > 1000ms

### Automatic Retraining ✅

Your model automatically retrains:
- **Schedule:** Every Sunday at 2 AM UTC
- **Process:** Fully automated pipeline
- **Result:** New model deployed if quality improves

---

## Daily Monitoring (5 minutes)

### Check Dashboard

1. Open dashboard (link above)
2. Look for:
   - ✅ Steady invocation rate
   - ✅ Latency < 500ms (P99)
   - ✅ Error rate < 5%
   - ✅ CPU < 80%
   - ✅ Memory < 85%

### Check Alarms

1. Open CloudWatch Alarms:
   ```
   https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:
   ```

2. Verify alarm status:
   - ✅ **OK** = Everything normal
   - ⏳ **INSUFFICIENT_DATA** = Normal for new endpoints
   - 🚨 **ALARM** = Investigate immediately

---

## When Alarms Trigger

### High Error Rate Alarm 🚨

**What it means:** > 5% of requests are failing

**What to do:**
1. Check CloudWatch Logs for error details
2. Verify input data format is correct
3. Check if endpoint is overloaded
4. Review recent changes

### High Latency Alarm 🚨

**What it means:** P99 latency > 1000ms

**What to do:**
1. Check if endpoint is under heavy load
2. Verify auto-scaling is working
3. Consider larger instance type
4. Check for cold starts

---

## Advanced Monitoring (Optional)

### Real-Time Metrics

Monitor metrics continuously:

```bash
python monitor_endpoint_metrics.py
```

This shows live updates every 60 seconds with:
- Current invocation rate
- Latest latency measurements
- Error counts and rates
- CPU and memory usage

### Check Monitoring Status

See complete monitoring setup:

```bash
python check_monitoring_status.py
```

This displays:
- Pipeline execution status
- Dashboard availability
- Alarm configuration
- SNS topic subscriptions

---

## Troubleshooting

### "No metrics showing in dashboard"

**Cause:** Endpoint hasn't received requests yet

**Solution:**
1. Run test script: `python test_endpoint_predictions.py`
2. Wait 5-10 minutes
3. Refresh dashboard

### "Alarms show INSUFFICIENT_DATA"

**Cause:** Not enough data collected yet (normal for new endpoints)

**Solution:**
1. Send more test requests
2. Wait 15-30 minutes
3. Status will change to OK once data is collected

### "Can't access CloudWatch/SNS"

**Cause:** IAM permissions issue

**Solution:**
1. Use AWS Console (links provided above)
2. Or request additional permissions from admin:
   - `cloudwatch:ListDashboards`
   - `cloudwatch:DescribeAlarms`
   - `sns:Subscribe`

---

## Cost Information

### Current Monthly Cost (Estimated)

- **SageMaker Endpoint:** ~$165/month (24/7 operation)
- **CloudWatch:** ~$3/month (dashboard + alarms)
- **S3 Storage:** ~$1/month
- **Lambda:** < $1/month (within free tier)

**Total:** ~$170/month

### Cost Optimization

To reduce costs:

1. **Stop endpoint when not needed:**
   ```bash
   aws sagemaker delete-endpoint --endpoint-name movielens-endpoint-20260123-122948
   ```

2. **Use smaller instance:**
   - Change to ml.t2.medium (~$47/month)

3. **Schedule endpoint:**
   - Run only during business hours
   - Stop overnight/weekends

---

## Quick Reference

### Important Links

| Resource | URL |
|----------|-----|
| **Dashboard** | https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards: |
| **Alarms** | https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2: |
| **SNS Topic** | https://console.aws.amazon.com/sns/v3/home?region=us-east-1#/topics |
| **Endpoint** | https://console.aws.amazon.com/sagemaker/home?region=us-east-1#/endpoints |

### Key Commands

```bash
# Test endpoint
python test_endpoint_predictions.py

# Check monitoring status
python check_monitoring_status.py

# Monitor real-time metrics
python monitor_endpoint_metrics.py

# Setup email alerts
python setup_email_alerts.py your-email@example.com
```

### Key Metrics

| Metric | Target | Alarm Threshold |
|--------|--------|-----------------|
| P99 Latency | < 500ms | > 1000ms |
| Error Rate | < 1% | > 5% |
| CPU Usage | 20-60% | Monitor if > 80% |
| Memory Usage | 30-70% | Monitor if > 85% |

---

## Next Steps

1. ✅ **Complete Step 1-3 above** (6 minutes total)
2. ⏳ **Monitor for 24 hours** to establish baseline
3. ⏳ **Adjust alarm thresholds** if needed
4. ⏳ **Document normal patterns** for your team
5. ⏳ **Wait for Sunday 2 AM UTC** to verify weekly retraining

---

## Support

### Documentation

- `DEPLOYMENT_SUCCESS.md` - Complete deployment summary
- `MONITORING_SETUP_GUIDE.md` - Detailed monitoring guide
- `MONITORING_WORKAROUND.md` - Console-based monitoring
- `RUNBOOK.md` - Operational procedures

### Scripts

- `test_endpoint_predictions.py` - Test endpoint
- `check_monitoring_status.py` - Check setup
- `monitor_endpoint_metrics.py` - Real-time monitoring
- `setup_email_alerts.py` - Configure alerts

---

**🎉 Congratulations! Your MovieLens recommendation system is production-ready!**

