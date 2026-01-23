"""
CloudWatch Monitoring Setup Module

This module provides functions to create CloudWatch dashboards and alarms
for monitoring SageMaker endpoint performance and health.

This module can be used both as a library and as an AWS Lambda function.
"""

import json
import boto3
from typing import Dict, List, Optional


def create_dashboard_configuration(
    endpoint_name: str,
    dashboard_name: Optional[str] = None,
    region: str = "us-east-1"
) -> Dict:
    """
    Create CloudWatch dashboard configuration for SageMaker endpoint monitoring.
    
    This function generates a dashboard configuration that displays:
    - Invocations per minute
    - Model latency (P50, P90, P99)
    - Error rates (4xx, 5xx)
    - Instance CPU and memory utilization
    
    Args:
        endpoint_name: Name of the SageMaker endpoint to monitor
        dashboard_name: Name for the dashboard (defaults to endpoint_name + "-dashboard")
        region: AWS region where the endpoint is deployed
        
    Returns:
        Dictionary containing dashboard configuration
        
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.7
    """
    if dashboard_name is None:
        dashboard_name = f"{endpoint_name}-dashboard"
    
    # Define the dashboard body with all required metrics
    dashboard_body = {
        "widgets": [
            # Invocations per minute widget
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/SageMaker",
                            "Invocations",
                            "EndpointName",
                            endpoint_name,
                            "VariantName",
                            "AllTraffic",
                            {"stat": "Sum", "period": 60}
                        ]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Invocations per Minute",
                    "period": 60,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            },
            # Model latency widget (P50, P90, P99)
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/SageMaker",
                            "ModelLatency",
                            "EndpointName",
                            endpoint_name,
                            "VariantName",
                            "AllTraffic",
                            {"stat": "p50", "label": "P50 Latency"}
                        ],
                        [
                            "...",
                            {"stat": "p90", "label": "P90 Latency"}
                        ],
                        [
                            "...",
                            {"stat": "p99", "label": "P99 Latency"}
                        ]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Model Latency (P50, P90, P99)",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Milliseconds"
                        }
                    }
                }
            },
            # Error rates widget (4xx and 5xx)
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/SageMaker",
                            "Invocation4XXErrors",
                            "EndpointName",
                            endpoint_name,
                            "VariantName",
                            "AllTraffic",
                            {"stat": "Sum", "label": "4xx Errors"}
                        ],
                        [
                            "AWS/SageMaker",
                            "Invocation5XXErrors",
                            "EndpointName",
                            endpoint_name,
                            "VariantName",
                            "AllTraffic",
                            {"stat": "Sum", "label": "5xx Errors"}
                        ]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Error Rates (4xx and 5xx)",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Count"
                        }
                    }
                }
            },
            # CPU utilization widget
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/SageMaker",
                            "CPUUtilization",
                            "EndpointName",
                            endpoint_name,
                            "VariantName",
                            "AllTraffic",
                            {"stat": "Average"}
                        ]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "CPU Utilization",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Percent",
                            "min": 0,
                            "max": 100
                        }
                    }
                }
            },
            # Memory utilization widget
            {
                "type": "metric",
                "properties": {
                    "metrics": [
                        [
                            "AWS/SageMaker",
                            "MemoryUtilization",
                            "EndpointName",
                            endpoint_name,
                            "VariantName",
                            "AllTraffic",
                            {"stat": "Average"}
                        ]
                    ],
                    "view": "timeSeries",
                    "stacked": False,
                    "region": region,
                    "title": "Memory Utilization",
                    "period": 300,
                    "yAxis": {
                        "left": {
                            "label": "Percent",
                            "min": 0,
                            "max": 100
                        }
                    }
                }
            }
        ]
    }
    
    return {
        "DashboardName": dashboard_name,
        "DashboardBody": json.dumps(dashboard_body)
    }


def create_high_error_rate_alarm(
    endpoint_name: str,
    sns_topic_arn: str,
    alarm_name: Optional[str] = None,
    threshold: float = 5.0,
    evaluation_periods: int = 2,
    datapoints_to_alarm: int = 2
) -> Dict:
    """
    Create CloudWatch alarm for high error rate (> 5%).
    
    This alarm triggers when the combined 4xx and 5xx error rate exceeds 5%
    of total invocations.
    
    Args:
        endpoint_name: Name of the SageMaker endpoint to monitor
        sns_topic_arn: ARN of SNS topic for alarm notifications
        alarm_name: Name for the alarm (defaults to endpoint_name + "-high-error-rate")
        threshold: Error rate threshold percentage (default: 5.0)
        evaluation_periods: Number of periods to evaluate (default: 2)
        datapoints_to_alarm: Number of datapoints that must breach threshold (default: 2)
        
    Returns:
        Dictionary containing alarm configuration
        
    Requirements: 7.5
    """
    if alarm_name is None:
        alarm_name = f"{endpoint_name}-high-error-rate"
    
    # Calculate error rate as percentage: (4xx + 5xx) / Invocations * 100
    alarm_config = {
        "AlarmName": alarm_name,
        "AlarmDescription": f"Alarm when error rate exceeds {threshold}% for {endpoint_name}",
        "ActionsEnabled": True,
        "AlarmActions": [sns_topic_arn],
        "MetricName": "Invocations",
        "Namespace": "AWS/SageMaker",
        "Statistic": "Sum",
        "Dimensions": [
            {
                "Name": "EndpointName",
                "Value": endpoint_name
            },
            {
                "Name": "VariantName",
                "Value": "AllTraffic"
            }
        ],
        "Period": 300,  # 5 minutes
        "EvaluationPeriods": evaluation_periods,
        "DatapointsToAlarm": datapoints_to_alarm,
        "Threshold": threshold,
        "ComparisonOperator": "GreaterThanThreshold",
        "TreatMissingData": "notBreaching",
        # Use metric math to calculate error rate percentage
        "Metrics": [
            {
                "Id": "invocations",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/SageMaker",
                        "MetricName": "Invocations",
                        "Dimensions": [
                            {
                                "Name": "EndpointName",
                                "Value": endpoint_name
                            },
                            {
                                "Name": "VariantName",
                                "Value": "AllTraffic"
                            }
                        ]
                    },
                    "Period": 300,
                    "Stat": "Sum"
                },
                "ReturnData": False
            },
            {
                "Id": "errors_4xx",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/SageMaker",
                        "MetricName": "Invocation4XXErrors",
                        "Dimensions": [
                            {
                                "Name": "EndpointName",
                                "Value": endpoint_name
                            },
                            {
                                "Name": "VariantName",
                                "Value": "AllTraffic"
                            }
                        ]
                    },
                    "Period": 300,
                    "Stat": "Sum"
                },
                "ReturnData": False
            },
            {
                "Id": "errors_5xx",
                "MetricStat": {
                    "Metric": {
                        "Namespace": "AWS/SageMaker",
                        "MetricName": "Invocation5XXErrors",
                        "Dimensions": [
                            {
                                "Name": "EndpointName",
                                "Value": endpoint_name
                            },
                            {
                                "Name": "VariantName",
                                "Value": "AllTraffic"
                            }
                        ]
                    },
                    "Period": 300,
                    "Stat": "Sum"
                },
                "ReturnData": False
            },
            {
                "Id": "error_rate",
                "Expression": "(errors_4xx + errors_5xx) / invocations * 100",
                "Label": "Error Rate (%)",
                "ReturnData": True
            }
        ]
    }
    
    return alarm_config


def create_high_latency_alarm(
    endpoint_name: str,
    sns_topic_arn: str,
    alarm_name: Optional[str] = None,
    threshold: float = 1000.0,
    evaluation_periods: int = 2,
    datapoints_to_alarm: int = 2
) -> Dict:
    """
    Create CloudWatch alarm for high latency (> 1000ms).
    
    This alarm triggers when P99 model latency exceeds 1000ms.
    
    Args:
        endpoint_name: Name of the SageMaker endpoint to monitor
        sns_topic_arn: ARN of SNS topic for alarm notifications
        alarm_name: Name for the alarm (defaults to endpoint_name + "-high-latency")
        threshold: Latency threshold in milliseconds (default: 1000.0)
        evaluation_periods: Number of periods to evaluate (default: 2)
        datapoints_to_alarm: Number of datapoints that must breach threshold (default: 2)
        
    Returns:
        Dictionary containing alarm configuration
        
    Requirements: 7.6
    """
    if alarm_name is None:
        alarm_name = f"{endpoint_name}-high-latency"
    
    alarm_config = {
        "AlarmName": alarm_name,
        "AlarmDescription": f"Alarm when P99 latency exceeds {threshold}ms for {endpoint_name}",
        "ActionsEnabled": True,
        "AlarmActions": [sns_topic_arn],
        "MetricName": "ModelLatency",
        "Namespace": "AWS/SageMaker",
        "Statistic": "p99",
        "Dimensions": [
            {
                "Name": "EndpointName",
                "Value": endpoint_name
            },
            {
                "Name": "VariantName",
                "Value": "AllTraffic"
            }
        ],
        "Period": 300,  # 5 minutes
        "EvaluationPeriods": evaluation_periods,
        "DatapointsToAlarm": datapoints_to_alarm,
        "Threshold": threshold,
        "ComparisonOperator": "GreaterThanThreshold",
        "TreatMissingData": "notBreaching"
    }
    
    return alarm_config


def create_monitoring_setup(
    endpoint_name: str,
    sns_topic_arn: str,
    region: str = "us-east-1",
    dashboard_name: Optional[str] = None,
    error_rate_threshold: float = 5.0,
    latency_threshold: float = 1000.0
) -> Dict:
    """
    Create complete monitoring setup including dashboard and alarms.
    
    This is a convenience function that creates both the CloudWatch dashboard
    and the required alarms for comprehensive endpoint monitoring.
    
    Args:
        endpoint_name: Name of the SageMaker endpoint to monitor
        sns_topic_arn: ARN of SNS topic for alarm notifications
        region: AWS region where the endpoint is deployed
        dashboard_name: Name for the dashboard (optional)
        error_rate_threshold: Error rate threshold percentage (default: 5.0)
        latency_threshold: Latency threshold in milliseconds (default: 1000.0)
        
    Returns:
        Dictionary containing dashboard and alarm configurations
        
    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
    """
    dashboard_config = create_dashboard_configuration(
        endpoint_name=endpoint_name,
        dashboard_name=dashboard_name,
        region=region
    )
    
    error_alarm_config = create_high_error_rate_alarm(
        endpoint_name=endpoint_name,
        sns_topic_arn=sns_topic_arn,
        threshold=error_rate_threshold
    )
    
    latency_alarm_config = create_high_latency_alarm(
        endpoint_name=endpoint_name,
        sns_topic_arn=sns_topic_arn,
        threshold=latency_threshold
    )
    
    return {
        "dashboard": dashboard_config,
        "alarms": {
            "high_error_rate": error_alarm_config,
            "high_latency": latency_alarm_config
        }
    }



def lambda_handler(event, context):
    """
    AWS Lambda handler for setting up monitoring for a SageMaker endpoint.
    
    This function is called by Step Functions after endpoint deployment to
    create CloudWatch dashboards and alarms.
    
    Expected event structure:
    {
        "endpoint_name": "movielens-endpoint-...",
        "bucket_name": "amzn-s3-movielens-..."
    }
    
    Args:
        event: Event data from Step Functions
        context: Lambda context object
        
    Returns:
        Dictionary with monitoring setup status
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Extract parameters from event
    endpoint_name = event.get('endpoint_name')
    bucket_name = event.get('bucket_name')
    
    if not endpoint_name:
        raise ValueError("endpoint_name is required in event")
    
    print(f"Setting up monitoring for endpoint: {endpoint_name}")
    
    # Initialize AWS clients
    cloudwatch = boto3.client('cloudwatch')
    sns = boto3.client('sns')
    sts = boto3.client('sts')
    
    # Get account ID for SNS topic ARN
    account_id = sts.get_caller_identity()['Account']
    region = context.invoked_function_arn.split(':')[3]
    
    # Create or get SNS topic for alarms
    topic_name = 'MovieLensEndpointAlarms'
    try:
        # Try to create topic (idempotent operation)
        topic_response = sns.create_topic(Name=topic_name)
        sns_topic_arn = topic_response['TopicArn']
        print(f"Using SNS topic: {sns_topic_arn}")
    except Exception as e:
        print(f"Error creating SNS topic: {e}")
        # Use default topic ARN format
        sns_topic_arn = f"arn:aws:sns:{region}:{account_id}:{topic_name}"
    
    # Create monitoring setup
    monitoring_config = create_monitoring_setup(
        endpoint_name=endpoint_name,
        sns_topic_arn=sns_topic_arn,
        region=region
    )
    
    # Create CloudWatch dashboard
    try:
        dashboard_config = monitoring_config['dashboard']
        cloudwatch.put_dashboard(
            DashboardName=dashboard_config['DashboardName'],
            DashboardBody=dashboard_config['DashboardBody']
        )
        print(f"Created dashboard: {dashboard_config['DashboardName']}")
    except Exception as e:
        print(f"Error creating dashboard: {e}")
        # Continue even if dashboard creation fails
    
    # Create CloudWatch alarms
    alarms_created = []
    for alarm_type, alarm_config in monitoring_config['alarms'].items():
        try:
            # Remove Metrics field if present (use MetricName instead for simple alarms)
            if 'Metrics' in alarm_config:
                # This is a metric math alarm (error rate)
                cloudwatch.put_metric_alarm(**alarm_config)
            else:
                # This is a simple alarm (latency)
                cloudwatch.put_metric_alarm(**alarm_config)
            
            alarm_name = alarm_config['AlarmName']
            alarms_created.append(alarm_name)
            print(f"Created alarm: {alarm_name}")
        except Exception as e:
            print(f"Error creating {alarm_type} alarm: {e}")
            # Continue even if alarm creation fails
    
    result = {
        'statusCode': 200,
        'endpoint_name': endpoint_name,
        'dashboard_created': True,
        'alarms_created': alarms_created,
        'sns_topic_arn': sns_topic_arn,
        'message': f'Monitoring setup completed for {endpoint_name}'
    }
    
    print(f"Monitoring setup result: {json.dumps(result)}")
    return result
