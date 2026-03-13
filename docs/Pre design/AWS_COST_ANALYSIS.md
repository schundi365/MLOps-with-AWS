# AWS Cost Analysis - Resources That Cost Money

## 🚨 HIGH COST - DELETE IMMEDIATELY WHEN NOT IN USE

### 1. SageMaker Endpoints (HIGHEST COST)
**Current Configuration:**
- Instance Type: `ml.m5.xlarge`
- Initial Instance Count: 2
- Auto-scaling: 1-5 instances

**Cost:** ~$0.269/hour per instance = **$6.46/day per instance**
- With 2 instances: **~$12.92/day** or **~$387/month**
- With 5 instances (max): **~$32.30/day** or **~$969/month**

**How to Delete:**
```python
import boto3
sagemaker = boto3.client('sagemaker')

# List all endpoints
response = sagemaker.list_endpoints()
for endpoint in response['Endpoints']:
    print(f"Deleting endpoint: {endpoint['EndpointName']}")
    sagemaker.delete_endpoint(EndpointName=endpoint['EndpointName'])
```

**Or via AWS CLI:**
```bash
# List endpoints
aws sagemaker list-endpoints

# Delete specific endpoint
aws sagemaker delete-endpoint --endpoint-name <endpoint-name>
```

### 2. SageMaker Training Jobs (When Running)
**Cost:** ~$1.26/hour for `ml.p3.2xlarge` (GPU instance)
- Typical training: 2-4 hours = **$2.52-$5.04 per run**
- Training jobs stop automatically when complete (no ongoing cost)

**Note:** Training jobs are transient - they only cost money while running.

### 3. NAT Gateway (If Deployed in VPC)
**Cost:** ~$0.045/hour + data transfer = **~$32.40/month**

**How to Check:**
```bash
aws ec2 describe-nat-gateways --filter "Name=state,Values=available"
```

**How to Delete:**
```bash
aws ec2 delete-nat-gateway --nat-gateway-id <nat-gateway-id>
```

## 💰 MEDIUM COST - MONITOR REGULARLY

### 4. EC2 Instances (If Running FastAPI Backend)
**Cost:** Depends on instance type
- t3.small: ~$0.0208/hour = **~$15/month**
- t3.medium: ~$0.0416/hour = **~$30/month**
- t3.large: ~$0.0832/hour = **~$60/month**

**How to Check:**
```bash
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"
```

**How to Stop:**
```bash
aws ec2 stop-instances --instance-ids <instance-id>
# Or terminate permanently:
aws ec2 terminate-instances --instance-ids <instance-id>
```

### 5. RDS Database (If Using PostgreSQL/MySQL)
**Cost:** Depends on instance type
- db.t3.micro: ~$0.017/hour = **~$12/month**
- db.t3.small: ~$0.034/hour = **~$25/month**
- db.t3.medium: ~$0.068/hour = **~$49/month**

**How to Check:**
```bash
aws rds describe-db-instances
```

**How to Stop (temporary):**
```bash
aws rds stop-db-instance --db-instance-identifier <db-instance-id>
```

**How to Delete (permanent):**
```bash
aws rds delete-db-instance --db-instance-identifier <db-instance-id> --skip-final-snapshot
```

### 6. ElastiCache Redis (If Used for Caching)
**Cost:** 
- cache.t3.micro: ~$0.017/hour = **~$12/month**
- cache.t3.small: ~$0.034/hour = **~$25/month**

**How to Check:**
```bash
aws elasticache describe-cache-clusters
```

**How to Delete:**
```bash
aws elasticache delete-cache-cluster --cache-cluster-id <cluster-id>
```

### 7. Application Load Balancer (If Used)
**Cost:** ~$0.0225/hour + data transfer = **~$16/month**

**How to Check:**
```bash
aws elbv2 describe-load-balancers
```

**How to Delete:**
```bash
aws elbv2 delete-load-balancer --load-balancer-arn <arn>
```

## 💵 LOW COST - MINIMAL ONGOING CHARGES

### 8. S3 Storage
**Cost:** ~$0.023/GB/month for Standard storage
- 10 GB: **~$0.23/month**
- 100 GB: **~$2.30/month**
- 1 TB: **~$23/month**

**How to Check Size:**
```bash
aws s3 ls s3://<bucket-name> --recursive --summarize
```

**Cost Optimization:**
- Enable lifecycle policies to move old data to Glacier
- Delete unnecessary model artifacts
- Enable Intelligent-Tiering

### 9. Lambda Functions
**Cost:** Pay per invocation + compute time
- First 1M requests/month: FREE
- After: $0.20 per 1M requests
- Compute: $0.0000166667 per GB-second

**Typical Monthly Cost:** **$0-$5** (unless very high traffic)

### 10. API Gateway
**Cost:** 
- First 1M requests: $3.50
- After: $3.50 per million requests

**Typical Monthly Cost:** **$0-$10** (unless very high traffic)

### 11. DynamoDB
**Cost:** On-demand pricing
- Write: $1.25 per million write request units
- Read: $0.25 per million read request units
- Storage: $0.25/GB/month

**Typical Monthly Cost:** **$0-$5** (for low traffic)

### 12. CloudWatch Logs
**Cost:** 
- Ingestion: $0.50/GB
- Storage: $0.03/GB/month

**Typical Monthly Cost:** **$1-$10**

**Cost Optimization:**
```bash
# Set log retention to 7 days instead of indefinite
aws logs put-retention-policy --log-group-name <log-group> --retention-in-days 7
```

## 🆓 FREE OR NEGLIGIBLE COST

### 13. Step Functions
**Cost:** $0.025 per 1,000 state transitions
- Weekly retraining: ~52 executions/year = **~$0.01/year**

### 14. EventBridge Rules
**Cost:** First 1M events: FREE
- Weekly trigger: **$0/month**

### 15. IAM Roles and Policies
**Cost:** **FREE**

### 16. CloudWatch Alarms
**Cost:** $0.10 per alarm/month
- 10 alarms: **$1/month**

### 17. SNS Topics
**Cost:** 
- First 1,000 email notifications: FREE
- After: $2 per 100,000 notifications

### 18. Cognito
**Cost:** 
- First 50,000 MAU (Monthly Active Users): FREE
- After: $0.0055 per MAU

## 📊 ESTIMATED MONTHLY COSTS BY SCENARIO

### Scenario 1: Development/Testing (Minimal Usage)
```
SageMaker Endpoint (1 instance, 8 hours/day): ~$65/month
S3 Storage (50 GB): ~$1.15/month
Lambda + API Gateway: ~$2/month
CloudWatch Logs: ~$2/month
DynamoDB: ~$1/month
Other services: ~$2/month
---
TOTAL: ~$73/month
```

### Scenario 2: Production (Always-On, Low Traffic)
```
SageMaker Endpoint (2 instances, 24/7): ~$387/month
S3 Storage (200 GB): ~$4.60/month
Lambda + API Gateway: ~$10/month
CloudWatch Logs: ~$5/month
DynamoDB: ~$5/month
Other services: ~$5/month
---
TOTAL: ~$417/month
```

### Scenario 3: Production (High Traffic with Auto-scaling)
```
SageMaker Endpoint (avg 3 instances, 24/7): ~$581/month
RDS Database (db.t3.small): ~$25/month
ElastiCache Redis: ~$12/month
S3 Storage (500 GB): ~$11.50/month
Lambda + API Gateway: ~$50/month
CloudWatch Logs: ~$15/month
DynamoDB: ~$20/month
Other services: ~$10/month
---
TOTAL: ~$725/month
```

## 🛡️ COST PROTECTION STRATEGIES

### 1. Set Up Billing Alarms
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# Create alarm for $50 threshold
cloudwatch.put_metric_alarm(
    AlarmName='BillingAlert-50USD',
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=1,
    MetricName='EstimatedCharges',
    Namespace='AWS/Billing',
    Period=21600,  # 6 hours
    Statistic='Maximum',
    Threshold=50.0,
    ActionsEnabled=True,
    AlarmActions=['arn:aws:sns:us-east-1:ACCOUNT_ID:billing-alerts'],
    AlarmDescription='Alert when charges exceed $50'
)
```

### 2. Use AWS Budgets
```bash
# Create a budget via AWS Console:
# AWS Console > Billing > Budgets > Create Budget
# Set monthly budget (e.g., $100) with email alerts at 80% and 100%
```

### 3. Enable Cost Explorer
- Go to AWS Console > Cost Management > Cost Explorer
- Analyze costs by service, region, and time period

### 4. Tag All Resources
```python
# Tag resources for cost tracking
sagemaker.add_tags(
    ResourceArn=endpoint_arn,
    Tags=[
        {'Key': 'Project', 'Value': 'MovieLens'},
        {'Key': 'Environment', 'Value': 'Development'},
        {'Key': 'Owner', 'Value': 'YourName'}
    ]
)
```

## 🔧 CLEANUP SCRIPT

Create this script to quickly tear down expensive resources:

```python
# cleanup_expensive_resources.py
import boto3

def cleanup_all():
    sagemaker = boto3.client('sagemaker')
    ec2 = boto3.client('ec2')
    rds = boto3.client('rds')
    
    # Delete SageMaker endpoints
    print("Deleting SageMaker endpoints...")
    endpoints = sagemaker.list_endpoints()['Endpoints']
    for endpoint in endpoints:
        name = endpoint['EndpointName']
        print(f"  Deleting {name}")
        sagemaker.delete_endpoint(EndpointName=name)
    
    # Stop EC2 instances
    print("\nStopping EC2 instances...")
    instances = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            print(f"  Stopping {instance_id}")
            ec2.stop_instances(InstanceIds=[instance_id])
    
    # Stop RDS instances
    print("\nStopping RDS instances...")
    db_instances = rds.describe_db_instances()['DBInstances']
    for db in db_instances:
        db_id = db['DBInstanceIdentifier']
        if db['DBInstanceStatus'] == 'available':
            print(f"  Stopping {db_id}")
            rds.stop_db_instance(DBInstanceIdentifier=db_id)
    
    print("\n✅ Cleanup complete!")

if __name__ == '__main__':
    response = input("This will stop/delete expensive resources. Continue? (yes/no): ")
    if response.lower() == 'yes':
        cleanup_all()
    else:
        print("Cancelled.")
```

## 📝 DAILY CHECKLIST

**Before Leaving for the Day:**
- [ ] Check if SageMaker endpoints are still needed
- [ ] Stop EC2 instances if not in use
- [ ] Stop RDS databases if not in use
- [ ] Review CloudWatch billing metrics

**Weekly:**
- [ ] Review AWS Cost Explorer
- [ ] Delete old S3 objects and logs
- [ ] Check for unused resources

**Monthly:**
- [ ] Review detailed billing report
- [ ] Optimize resource usage based on actual needs
- [ ] Consider Reserved Instances for long-term resources

## 🚀 QUICK COMMANDS

```bash
# Check current month's estimated charges
aws cloudwatch get-metric-statistics \
  --namespace AWS/Billing \
  --metric-name EstimatedCharges \
  --dimensions Name=Currency,Value=USD \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Maximum

# List all running resources (summary)
echo "=== SageMaker Endpoints ==="
aws sagemaker list-endpoints --query 'Endpoints[?EndpointStatus==`InService`].[EndpointName]' --output table

echo "=== EC2 Instances ==="
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" --query 'Reservations[].Instances[].[InstanceId,InstanceType]' --output table

echo "=== RDS Instances ==="
aws rds describe-db-instances --query 'DBInstances[?DBInstanceStatus==`available`].[DBInstanceIdentifier,DBInstanceClass]' --output table
```

## 💡 COST OPTIMIZATION TIPS

1. **Use SageMaker Serverless Inference** for low-traffic endpoints (pay per request)
2. **Use Spot Instances** for training jobs (up to 90% savings)
3. **Enable S3 Intelligent-Tiering** for automatic cost optimization
4. **Set CloudWatch log retention** to 7-14 days instead of indefinite
5. **Use Reserved Instances** if running 24/7 for >1 year (up to 75% savings)
6. **Delete old model artifacts** from S3 after deployment
7. **Use Lambda instead of EC2** when possible (pay per use)
8. **Enable auto-scaling** to scale down during low traffic
9. **Use CloudFront caching** to reduce API Gateway costs
10. **Monitor and delete unused resources** regularly

---

**⚠️ REMEMBER:** The SageMaker endpoint is by far your biggest cost. If you're not actively using it, delete it immediately!
