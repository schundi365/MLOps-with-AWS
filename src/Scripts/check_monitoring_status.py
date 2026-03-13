#!/usr/bin/env python3
"""
Check Monitoring Status

This script checks the status of CloudWatch monitoring for your MovieLens endpoint:
- Lists CloudWatch dashboards
- Lists CloudWatch alarms
- Shows SNS topic details
- Provides instructions for setting up email alerts
"""

import boto3
import json
from datetime import datetime

def check_monitoring_status():
    """Check the status of monitoring setup."""
    
    # Initialize AWS clients
    cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
    sns = boto3.client('sns', region_name='us-east-1')
    sts = boto3.client('sts', region_name='us-east-1')
    stepfunctions = boto3.client('stepfunctions', region_name='us-east-1')
    
    # Get account ID
    account_id = sts.get_caller_identity()['Account']
    
    print("=" * 80)
    print("MOVIELENS MONITORING STATUS")
    print("=" * 80)
    print()
    
    # Check pipeline execution status
    print("1. PIPELINE EXECUTION STATUS")
    print("-" * 80)
    try:
        state_machine_arn = f"arn:aws:states:us-east-1:{account_id}:stateMachine:MovieLensMLPipeline"
        
        # Get latest execution
        executions = stepfunctions.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=1,
            statusFilter='RUNNING'
        )
        
        if executions['executions']:
            execution = executions['executions'][0]
            execution_arn = execution['executionArn']
            execution_name = execution['name']
            status = execution['status']
            start_time = execution['startDate']
            
            print(f"   Execution Name: {execution_name}")
            print(f"   Status: {status}")
            print(f"   Started: {start_time}")
            
            # Get execution details
            details = stepfunctions.describe_execution(executionArn=execution_arn)
            
            # Try to parse output to get endpoint name
            if 'output' in details and details['output']:
                try:
                    output = json.loads(details['output'])
                    endpoint_name = output.get('endpoint_name')
                    if endpoint_name:
                        print(f"   Endpoint Name: {endpoint_name}")
                except:
                    pass
            
            print()
            print("   ⏳ Pipeline is still running. Monitoring will be set up when it completes.")
            print()
        else:
            # Check for completed executions
            executions = stepfunctions.list_executions(
                stateMachineArn=state_machine_arn,
                maxResults=1,
                statusFilter='SUCCEEDED'
            )
            
            if executions['executions']:
                execution = executions['executions'][0]
                execution_arn = execution['executionArn']
                execution_name = execution['name']
                status = execution['status']
                
                print(f"   Execution Name: {execution_name}")
                print(f"   Status: ✅ {status}")
                
                # Get execution output
                details = stepfunctions.describe_execution(executionArn=execution_arn)
                if 'output' in details and details['output']:
                    output = json.loads(details['output'])
                    endpoint_name = output.get('endpoint_name')
                    if endpoint_name:
                        print(f"   Endpoint Name: {endpoint_name}")
                print()
    except Exception as e:
        print(f"   Error checking pipeline: {e}")
        print()
    
    # Check CloudWatch dashboards
    print("2. CLOUDWATCH DASHBOARDS")
    print("-" * 80)
    try:
        dashboards = cloudwatch.list_dashboards()
        
        movielens_dashboards = [d for d in dashboards['DashboardEntries'] 
                               if 'movielens' in d['DashboardName'].lower()]
        
        if movielens_dashboards:
            for dashboard in movielens_dashboards:
                print(f"   ✅ Dashboard: {dashboard['DashboardName']}")
                print(f"      Last Modified: {dashboard.get('LastModified', 'N/A')}")
                print(f"      URL: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name={dashboard['DashboardName']}")
                print()
        else:
            print("   ⚠️  No MovieLens dashboards found yet.")
            print("      Dashboards will be created when the pipeline completes.")
            print()
    except Exception as e:
        print(f"   Error listing dashboards: {e}")
        print()
    
    # Check CloudWatch alarms
    print("3. CLOUDWATCH ALARMS")
    print("-" * 80)
    try:
        alarms = cloudwatch.describe_alarms(AlarmNamePrefix='movielens-endpoint')
        
        if alarms['MetricAlarms']:
            for alarm in alarms['MetricAlarms']:
                state = alarm['StateValue']
                state_icon = "✅" if state == "OK" else "⚠️" if state == "INSUFFICIENT_DATA" else "🚨"
                
                print(f"   {state_icon} Alarm: {alarm['AlarmName']}")
                print(f"      State: {state}")
                print(f"      Threshold: {alarm.get('Threshold', 'N/A')}")
                print(f"      Description: {alarm.get('AlarmDescription', 'N/A')}")
                print()
        else:
            print("   ⚠️  No MovieLens alarms found yet.")
            print("      Alarms will be created when the pipeline completes.")
            print()
    except Exception as e:
        print(f"   Error listing alarms: {e}")
        print()
    
    # Check SNS topic
    print("4. SNS TOPIC FOR ALERTS")
    print("-" * 80)
    try:
        topic_arn = f"arn:aws:sns:us-east-1:{account_id}:MovieLensEndpointAlarms"
        
        try:
            # Check if topic exists
            topic_attrs = sns.get_topic_attributes(TopicArn=topic_arn)
            print(f"   ✅ SNS Topic: MovieLensEndpointAlarms")
            print(f"      ARN: {topic_arn}")
            
            # Check subscriptions
            subscriptions = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
            
            if subscriptions['Subscriptions']:
                print(f"      Subscriptions: {len(subscriptions['Subscriptions'])}")
                for sub in subscriptions['Subscriptions']:
                    protocol = sub['Protocol']
                    endpoint = sub['Endpoint']
                    status = sub['SubscriptionArn']
                    
                    if status == 'PendingConfirmation':
                        print(f"         - {protocol}: {endpoint} (⏳ Pending Confirmation)")
                    else:
                        print(f"         - {protocol}: {endpoint} (✅ Confirmed)")
            else:
                print(f"      Subscriptions: None")
                print()
                print("   📧 TO SET UP EMAIL ALERTS:")
                print(f"      aws sns subscribe \\")
                print(f"        --topic-arn {topic_arn} \\")
                print(f"        --protocol email \\")
                print(f"        --notification-endpoint YOUR-EMAIL@example.com \\")
                print(f"        --region us-east-1")
                print()
                print("      Then check your email and confirm the subscription.")
            print()
        except sns.exceptions.NotFoundException:
            print(f"   ⚠️  SNS Topic not created yet.")
            print(f"      Topic will be created when the pipeline completes.")
            print()
    except Exception as e:
        print(f"   Error checking SNS topic: {e}")
        print()
    
    # Provide next steps
    print("5. NEXT STEPS")
    print("-" * 80)
    print()
    print("   After the pipeline completes successfully:")
    print()
    print("   1. Subscribe to SNS topic for email alerts:")
    print(f"      aws sns subscribe \\")
    print(f"        --topic-arn arn:aws:sns:us-east-1:{account_id}:MovieLensEndpointAlarms \\")
    print(f"        --protocol email \\")
    print(f"        --notification-endpoint YOUR-EMAIL@example.com \\")
    print(f"        --region us-east-1")
    print()
    print("   2. View CloudWatch dashboard:")
    print("      https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:")
    print()
    print("   3. View CloudWatch alarms:")
    print("      https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:")
    print()
    print("   4. Test endpoint predictions:")
    print("      python test_predictions.py")
    print()
    print("   5. Monitor metrics in real-time:")
    print("      python monitor_endpoint_metrics.py")
    print()
    print("=" * 80)


if __name__ == "__main__":
    check_monitoring_status()
