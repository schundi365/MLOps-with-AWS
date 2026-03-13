#!/usr/bin/env python3
"""Quick script to check currently running AWS resources that cost money."""

import boto3
from datetime import datetime, timedelta

def check_sagemaker_endpoints():
    """Check running SageMaker endpoints (HIGHEST COST)"""
    sagemaker = boto3.client('sagemaker')
    endpoints = []
    
    try:
        response = sagemaker.list_endpoints()
        for endpoint in response['Endpoints']:
            if endpoint['EndpointStatus'] == 'InService':
                details = sagemaker.describe_endpoint(EndpointName=endpoint['EndpointName'])
                config = sagemaker.describe_endpoint_config(
                    EndpointConfigName=details['EndpointConfigName']
                )
                
                instance_type = config['ProductionVariants'][0]['InstanceType']
                instance_count = config['ProductionVariants'][0]['InitialInstanceCount']
                
                cost_per_hour = {'ml.m5.xlarge': 0.269, 'ml.m5.2xlarge': 0.538}
                hourly_cost = cost_per_hour.get(instance_type, 0.269) * instance_count
                
                endpoints.append({
                    'name': endpoint['EndpointName'],
                    'instance_type': instance_type,
                    'instance_count': instance_count,
                    'hourly_cost': hourly_cost,
                    'daily_cost': hourly_cost * 24,
                    'monthly_cost': hourly_cost * 24 * 30
                })
    except Exception as e:
        print(f"Error: {e}")
    
    return endpoints

def main():
    print("AWS COST CHECKER")
    print("=" * 60)
    
    endpoints = check_sagemaker_endpoints()
    total_monthly = 0
    
    if endpoints:
        print("\nSAGEMAKER ENDPOINTS (RUNNING):")
        for ep in endpoints:
            print(f"  {ep['name']}: ${ep['monthly_cost']:.2f}/month")
            total_monthly += ep['monthly_cost']
    else:
        print("\n✅ No SageMaker endpoints running")
    
    print(f"\nESTIMATED MONTHLY COST: ${total_monthly:.2f}")
    
    if total_monthly > 100:
        print("\n⚠️  WARNING: High costs detected!")

if __name__ == '__main__':
    main()
