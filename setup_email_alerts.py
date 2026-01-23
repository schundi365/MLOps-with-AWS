#!/usr/bin/env python3
"""
Setup Email Alerts for MovieLens Endpoint

This script helps you subscribe to SNS topic for email alerts when
CloudWatch alarms trigger (high error rate or high latency).
"""

import boto3
import sys

def setup_email_alerts(email_address: str):
    """Subscribe email address to SNS topic for alerts."""
    
    # Initialize AWS clients
    sns = boto3.client('sns', region_name='us-east-1')
    sts = boto3.client('sts', region_name='us-east-1')
    
    # Get account ID
    account_id = sts.get_caller_identity()['Account']
    topic_arn = f"arn:aws:sns:us-east-1:{account_id}:MovieLensEndpointAlarms"
    
    print("=" * 80)
    print("SETUP EMAIL ALERTS FOR MOVIELENS ENDPOINT")
    print("=" * 80)
    print()
    
    # Check if topic exists
    try:
        topic_attrs = sns.get_topic_attributes(TopicArn=topic_arn)
        print(f"✅ SNS Topic found: MovieLensEndpointAlarms")
        print(f"   ARN: {topic_arn}")
        print()
    except sns.exceptions.NotFoundException:
        print(f"❌ SNS Topic not found: MovieLensEndpointAlarms")
        print()
        print("The SNS topic will be created when the pipeline completes.")
        print("Please wait for the pipeline to finish, then run this script again.")
        print()
        return False
    
    # Check if email is already subscribed
    subscriptions = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
    
    for sub in subscriptions['Subscriptions']:
        if sub['Protocol'] == 'email' and sub['Endpoint'] == email_address:
            if sub['SubscriptionArn'] == 'PendingConfirmation':
                print(f"⏳ Email {email_address} is already subscribed but pending confirmation.")
                print()
                print("Please check your email and click the confirmation link.")
                print()
                return True
            else:
                print(f"✅ Email {email_address} is already subscribed and confirmed.")
                print()
                return True
    
    # Subscribe email to topic
    try:
        print(f"📧 Subscribing {email_address} to alerts...")
        
        response = sns.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email_address,
            ReturnSubscriptionArn=True
        )
        
        subscription_arn = response['SubscriptionArn']
        
        print()
        print(f"✅ Subscription request sent!")
        print()
        print("IMPORTANT: Check your email inbox for a confirmation message.")
        print()
        print("You will receive an email from AWS Notifications with subject:")
        print("  'AWS Notification - Subscription Confirmation'")
        print()
        print("Click the 'Confirm subscription' link in the email to complete setup.")
        print()
        print("Once confirmed, you will receive email alerts when:")
        print("  - Error rate exceeds 5%")
        print("  - P99 latency exceeds 1000ms")
        print()
        
        return True
        
    except Exception as e:
        print(f"❌ Error subscribing email: {e}")
        print()
        return False


def list_current_subscriptions():
    """List all current subscriptions to the SNS topic."""
    
    # Initialize AWS clients
    sns = boto3.client('sns', region_name='us-east-1')
    sts = boto3.client('sts', region_name='us-east-1')
    
    # Get account ID
    account_id = sts.get_caller_identity()['Account']
    topic_arn = f"arn:aws:sns:us-east-1:{account_id}:MovieLensEndpointAlarms"
    
    print("=" * 80)
    print("CURRENT EMAIL ALERT SUBSCRIPTIONS")
    print("=" * 80)
    print()
    
    try:
        # Check if topic exists
        topic_attrs = sns.get_topic_attributes(TopicArn=topic_arn)
        
        # List subscriptions
        subscriptions = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
        
        if subscriptions['Subscriptions']:
            print(f"Found {len(subscriptions['Subscriptions'])} subscription(s):")
            print()
            
            for i, sub in enumerate(subscriptions['Subscriptions'], 1):
                protocol = sub['Protocol']
                endpoint = sub['Endpoint']
                status = sub['SubscriptionArn']
                
                print(f"{i}. {protocol.upper()}: {endpoint}")
                
                if status == 'PendingConfirmation':
                    print(f"   Status: ⏳ Pending Confirmation")
                    print(f"   Action: Check email and click confirmation link")
                else:
                    print(f"   Status: ✅ Confirmed")
                    print(f"   ARN: {status}")
                print()
        else:
            print("No subscriptions found.")
            print()
            print("Run this script with an email address to subscribe:")
            print(f"  python setup_email_alerts.py YOUR-EMAIL@example.com")
            print()
            
    except sns.exceptions.NotFoundException:
        print("SNS Topic not found yet.")
        print()
        print("The topic will be created when the pipeline completes.")
        print()
    except Exception as e:
        print(f"Error listing subscriptions: {e}")
        print()


def main():
    """Main function."""
    
    if len(sys.argv) < 2:
        print()
        print("Usage:")
        print(f"  python {sys.argv[0]} YOUR-EMAIL@example.com")
        print()
        print("Or to list current subscriptions:")
        print(f"  python {sys.argv[0]} --list")
        print()
        print("Example:")
        print(f"  python {sys.argv[0]} john.doe@example.com")
        print()
        sys.exit(1)
    
    if sys.argv[1] == '--list':
        list_current_subscriptions()
    else:
        email_address = sys.argv[1]
        
        # Basic email validation
        if '@' not in email_address or '.' not in email_address:
            print(f"Error: '{email_address}' does not appear to be a valid email address.")
            print()
            sys.exit(1)
        
        setup_email_alerts(email_address)


if __name__ == "__main__":
    main()
