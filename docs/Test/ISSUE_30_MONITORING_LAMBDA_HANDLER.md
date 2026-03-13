# Issue #30: Missing Lambda Handler in Monitoring Function - FIXED

## Problem Summary

Pipeline failed at the EnableMonitoring step with:
```
Handler 'lambda_handler' missing on module 'monitoring'
errorType: Runtime.HandlerNotFound
```

The monitoring Lambda function (`movielens-monitoring-setup`) was missing the `lambda_handler` function.

## Root Cause

The `src/monitoring.py` file only contained utility functions for creating CloudWatch dashboards and alarms, but did not have a `lambda_handler` function that AWS Lambda could invoke.

### What Was Missing

The file had these functions:
- `create_dashboard_configuration()`
- `create_high_error_rate_alarm()`
- `create_high_latency_alarm()`
- `create_monitoring_setup()`

But was missing:
- ❌ `lambda_handler(event, context)` - Required entry point for Lambda

## Solution

### 1. Added Lambda Handler Function

Added a `lambda_handler` function to `src/monitoring.py` that:
1. Extracts `endpoint_name` and `bucket_name` from the event
2. Creates or gets an SNS topic for alarm notifications
3. Creates CloudWatch dashboard with endpoint metrics
4. Creates CloudWatch alarms for high error rate and high latency
5. Returns status information

```python
def lambda_handler(event, context):
    """
    AWS Lambda handler for setting up monitoring for a SageMaker endpoint.
    
    Expected event structure:
    {
        "endpoint_name": "movielens-endpoint-...",
        "bucket_name": "amzn-s3-movielens-..."
    }
    """
    # Extract parameters
    endpoint_name = event.get('endpoint_name')
    
    # Create SNS topic
    sns_topic_arn = ...
    
    # Create monitoring setup
    monitoring_config = create_monitoring_setup(...)
    
    # Create dashboard and alarms
    cloudwatch.put_dashboard(...)
    cloudwatch.put_metric_alarm(...)
    
    return {
        'statusCode': 200,
        'endpoint_name': endpoint_name,
        'message': f'Monitoring setup completed for {endpoint_name}'
    }
```

### 2. Redeployed Lambda Function

Created and executed `redeploy_monitoring_lambda.py` to update the Lambda function code with the new handler.

## Implementation

### Script Created: `redeploy_monitoring_lambda.py`

This script:
1. Creates a deployment package with `monitoring.py`
2. Updates the Lambda function code
3. Verifies the update was successful

### Execution

```bash
python redeploy_monitoring_lambda.py
```

**Result:**
- ✓ Function updated: `movielens-monitoring-setup`
- ✓ Handler: `monitoring.lambda_handler`
- ✓ Last Modified: 2026-01-23 12:28:09 UTC

## Current Status

✅ **FIXED** - Monitoring Lambda function now has the required handler.

**Note:** The current pipeline execution (`execution-20260123-120004-complete-fix`) failed before the fix was applied. A new execution will be needed to verify the complete end-to-end pipeline.

## Files Modified

### Modified
1. `src/monitoring.py` - Added `lambda_handler` function and `boto3` import

### Created
1. `list_lambda_functions.py` - Script to list Lambda functions
2. `redeploy_monitoring_lambda.py` - Script to redeploy monitoring Lambda
3. `ISSUE_30_MONITORING_LAMBDA_HANDLER.md` - This document

## Lambda Handler Details

### Event Structure
```json
{
  "endpoint_name": "movielens-endpoint-20260123-120004",
  "bucket_name": "amzn-s3-movielens-327030626634"
}
```

### Return Structure
```json
{
  "statusCode": 200,
  "endpoint_name": "movielens-endpoint-20260123-120004",
  "dashboard_created": true,
  "alarms_created": [
    "movielens-endpoint-20260123-120004-high-error-rate",
    "movielens-endpoint-20260123-120004-high-latency"
  ],
  "sns_topic_arn": "arn:aws:sns:us-east-1:327030626634:MovieLensEndpointAlarms",
  "message": "Monitoring setup completed for movielens-endpoint-20260123-120004"
}
```

### Monitoring Components Created

1. **CloudWatch Dashboard**
   - Invocations per minute
   - Model latency (P50, P90, P99)
   - Error rates (4xx, 5xx)
   - CPU utilization
   - Memory utilization

2. **CloudWatch Alarms**
   - High error rate alarm (> 5%)
   - High latency alarm (> 1000ms P99)

3. **SNS Topic**
   - Topic name: `MovieLensEndpointAlarms`
   - Used for alarm notifications

## Key Learnings

### 1. Lambda Function Requirements
Every Lambda function must have an entry point function that matches the handler configuration:
- Handler format: `module.function_name`
- Example: `monitoring.lambda_handler` requires `lambda_handler` function in `monitoring.py`

### 2. Library vs Lambda Module
When a Python module serves dual purposes (library + Lambda), it needs:
- Utility functions for library use
- `lambda_handler` function for Lambda invocation

### 3. Testing Lambda Functions
Before deploying to production:
1. Verify the handler function exists
2. Test with sample events
3. Check CloudWatch Logs for errors

## Prevention

### 1. Add Lambda Handler Template
Create a template for Lambda functions:

```python
def lambda_handler(event, context):
    """
    AWS Lambda handler.
    
    Args:
        event: Event data
        context: Lambda context
        
    Returns:
        Response dictionary
    """
    try:
        # Extract parameters
        # Process request
        # Return result
        return {
            'statusCode': 200,
            'message': 'Success'
        }
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'error': str(e)
        }
```

### 2. Validate Lambda Deployment
Add validation to check:
- Handler function exists in module
- Function signature is correct
- Required imports are present

### 3. Integration Tests
Create tests that:
- Deploy Lambda function
- Invoke with sample event
- Verify response structure

## Related Issues

- **Issue #28**: Hyperparameter names
- **Issue #29**: Missing SageMaker parameters
- **Issue #30**: This issue - missing Lambda handler

## Timeline

| Time (UTC) | Event |
|------------|-------|
| 12:00:06 | Pipeline execution started |
| 12:18:14 | Pipeline failed at EnableMonitoring step |
| 12:25:00 | Root cause identified (missing handler) |
| 12:28:09 | Monitoring Lambda redeployed with handler |

## Next Steps

1. ✅ Monitoring Lambda fixed
2. ⏳ Restart pipeline execution
3. ⏳ Verify complete end-to-end execution
4. ⏳ Test endpoint predictions
5. ⏳ Validate all success criteria

## Success Criteria

### Lambda Function
- ✅ Handler function exists
- ✅ Function deployed successfully
- ⏳ Function executes without errors
- ⏳ Dashboard and alarms created

### Pipeline
- ⏳ Complete end-to-end execution
- ⏳ All steps succeed
- ⏳ Endpoint deployed and InService
- ⏳ Monitoring enabled

## References

- AWS Lambda Handler Documentation: https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html
- CloudWatch Dashboards: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Dashboards.html
- CloudWatch Alarms: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html

---

**Last Updated:** 2026-01-23 12:30 UTC  
**Status:** ✅ FIXED - Ready for Pipeline Restart
