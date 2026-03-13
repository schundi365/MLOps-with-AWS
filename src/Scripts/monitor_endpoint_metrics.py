#!/usr/bin/env python3
"""
Monitor Endpoint Metrics in Real-Time

This script continuously monitors your SageMaker endpoint metrics and displays them
in a user-friendly format. It shows:
- Invocations per minute
- Latency (P50, P90, P99)
- Error rates
- CPU and memory utilization
"""

import boto3
import time
from datetime import datetime, timedelta
from typing import Dict, Optional

def get_endpoint_name() -> Optional[str]:
    """Get the latest endpoint name from Step Functions execution."""
    try:
        sts = boto3.client('sts', region_name='us-east-1')
        account_id = sts.get_caller_identity()['Account']
        
        stepfunctions = boto3.client('stepfunctions', region_name='us-east-1')
        state_machine_arn = f"arn:aws:states:us-east-1:{account_id}:stateMachine:MovieLensMLPipeline"
        
        # Get latest successful execution
        executions = stepfunctions.list_executions(
            stateMachineArn=state_machine_arn,
            maxResults=1,
            statusFilter='SUCCEEDED'
        )
        
        if executions['executions']:
            execution_arn = executions['executions'][0]['executionArn']
            details = stepfunctions.describe_execution(executionArn=execution_arn)
            
            if 'output' in details and details['output']:
                import json
                output = json.loads(details['output'])
                return output.get('endpoint_name')
    except Exception as e:
        print(f"Error getting endpoint name: {e}")
    
    return None


def get_metric_statistics(
    cloudwatch,
    endpoint_name: str,
    metric_name: str,
    statistic: str,
    period: int = 300
) -> Optional[float]:
    """Get metric statistics from CloudWatch."""
    try:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=10)
        
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/SageMaker',
            MetricName=metric_name,
            Dimensions=[
                {'Name': 'EndpointName', 'Value': endpoint_name},
                {'Name': 'VariantName', 'Value': 'AllTraffic'}
            ],
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[statistic]
        )
        
        if response['Datapoints']:
            # Get the most recent datapoint
            datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
            return datapoints[0][statistic]
    except Exception as e:
        print(f"Error getting {metric_name}: {e}")
    
    return None


def format_metric(value: Optional[float], unit: str = "", decimals: int = 2) -> str:
    """Format metric value for display."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}{unit}"


def monitor_endpoint(endpoint_name: str, refresh_interval: int = 60):
    """Monitor endpoint metrics continuously."""
    cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
    
    print(f"Monitoring endpoint: {endpoint_name}")
    print(f"Refresh interval: {refresh_interval} seconds")
    print(f"Press Ctrl+C to stop")
    print()
    
    try:
        while True:
            print("=" * 80)
            print(f"ENDPOINT METRICS - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print("=" * 80)
            print()
            
            # Get invocations
            invocations = get_metric_statistics(
                cloudwatch, endpoint_name, 'Invocations', 'Sum', period=60
            )
            print(f"📊 Invocations (last minute): {format_metric(invocations, '', 0)}")
            print()
            
            # Get latency metrics
            print("⏱️  Latency:")
            latency_p50 = get_metric_statistics(
                cloudwatch, endpoint_name, 'ModelLatency', 'p50'
            )
            latency_p90 = get_metric_statistics(
                cloudwatch, endpoint_name, 'ModelLatency', 'p90'
            )
            latency_p99 = get_metric_statistics(
                cloudwatch, endpoint_name, 'ModelLatency', 'p99'
            )
            
            print(f"   P50: {format_metric(latency_p50, 'ms')} (median)")
            print(f"   P90: {format_metric(latency_p90, 'ms')}")
            print(f"   P99: {format_metric(latency_p99, 'ms')}")
            
            # Check if P99 meets requirement
            if latency_p99 is not None:
                if latency_p99 < 500:
                    print(f"   ✅ P99 latency meets requirement (< 500ms)")
                elif latency_p99 < 1000:
                    print(f"   ⚠️  P99 latency acceptable but above target (< 1000ms)")
                else:
                    print(f"   🚨 P99 latency exceeds threshold (> 1000ms)")
            print()
            
            # Get error rates
            print("❌ Errors:")
            errors_4xx = get_metric_statistics(
                cloudwatch, endpoint_name, 'Invocation4XXErrors', 'Sum'
            )
            errors_5xx = get_metric_statistics(
                cloudwatch, endpoint_name, 'Invocation5XXErrors', 'Sum'
            )
            
            print(f"   4xx Errors: {format_metric(errors_4xx, '', 0)}")
            print(f"   5xx Errors: {format_metric(errors_5xx, '', 0)}")
            
            # Calculate error rate
            if invocations and invocations > 0:
                total_errors = (errors_4xx or 0) + (errors_5xx or 0)
                error_rate = (total_errors / invocations) * 100
                print(f"   Error Rate: {format_metric(error_rate, '%')}")
                
                if error_rate < 5:
                    print(f"   ✅ Error rate within threshold (< 5%)")
                else:
                    print(f"   🚨 Error rate exceeds threshold (> 5%)")
            print()
            
            # Get CPU utilization
            cpu_util = get_metric_statistics(
                cloudwatch, endpoint_name, 'CPUUtilization', 'Average'
            )
            print(f"💻 CPU Utilization: {format_metric(cpu_util, '%')}")
            
            if cpu_util is not None:
                if cpu_util < 60:
                    print(f"   ✅ Normal")
                elif cpu_util < 80:
                    print(f"   ⚠️  Elevated")
                else:
                    print(f"   🚨 High - consider scaling")
            print()
            
            # Get memory utilization
            mem_util = get_metric_statistics(
                cloudwatch, endpoint_name, 'MemoryUtilization', 'Average'
            )
            print(f"🧠 Memory Utilization: {format_metric(mem_util, '%')}")
            
            if mem_util is not None:
                if mem_util < 70:
                    print(f"   ✅ Normal")
                elif mem_util < 85:
                    print(f"   ⚠️  Elevated")
                else:
                    print(f"   🚨 High - consider scaling")
            print()
            
            print(f"Next refresh in {refresh_interval} seconds...")
            print()
            
            time.sleep(refresh_interval)
            
    except KeyboardInterrupt:
        print()
        print("Monitoring stopped.")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor SageMaker endpoint metrics')
    parser.add_argument(
        '--endpoint-name',
        type=str,
        help='Endpoint name (auto-detected if not provided)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Refresh interval in seconds (default: 60)'
    )
    
    args = parser.parse_args()
    
    endpoint_name = args.endpoint_name
    
    if not endpoint_name:
        print("Auto-detecting endpoint name...")
        endpoint_name = get_endpoint_name()
        
        if not endpoint_name:
            print("Error: Could not auto-detect endpoint name.")
            print("Please provide endpoint name using --endpoint-name")
            return
    
    monitor_endpoint(endpoint_name, args.interval)


if __name__ == "__main__":
    main()
