#!/usr/bin/env python3
"""
Test MovieLens Endpoint Predictions

This script tests the deployed SageMaker endpoint with sample user-movie pairs
and displays the predicted ratings.
"""

import boto3
import json
import time
from datetime import datetime

def test_endpoint(endpoint_name: str = None):
    """Test the endpoint with sample predictions."""
    
    # Initialize clients
    runtime = boto3.client('sagemaker-runtime', region_name='us-east-1')
    
    # Auto-detect endpoint name if not provided
    if not endpoint_name:
        try:
            sts = boto3.client('sts', region_name='us-east-1')
            account_id = sts.get_caller_identity()['Account']
            
            stepfunctions = boto3.client('stepfunctions', region_name='us-east-1')
            state_machine_arn = f"arn:aws:states:us-east-1:{account_id}:stateMachine:MovieLensMLPipeline"
            
            executions = stepfunctions.list_executions(
                stateMachineArn=state_machine_arn,
                maxResults=1,
                statusFilter='SUCCEEDED'
            )
            
            if executions['executions']:
                execution_arn = executions['executions'][0]['executionArn']
                details = stepfunctions.describe_execution(executionArn=execution_arn)
                
                if 'output' in details and details['output']:
                    output = json.loads(details['output'])
                    endpoint_name = output.get('endpoint_name')
        except Exception as e:
            print(f"Error auto-detecting endpoint: {e}")
    
    if not endpoint_name:
        print("Error: Could not determine endpoint name.")
        print("Please provide endpoint name using --endpoint-name")
        return
    
    print("=" * 80)
    print("MOVIELENS ENDPOINT PREDICTION TEST")
    print("=" * 80)
    print()
    print(f"Endpoint: {endpoint_name}")
    print(f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print()
    
    # Test data: various user-movie combinations
    test_cases = [
        {"user_id": 1, "movie_id": 1, "description": "User 1, Movie 1 (Toy Story)"},
        {"user_id": 1, "movie_id": 50, "description": "User 1, Movie 50 (Star Wars)"},
        {"user_id": 10, "movie_id": 100, "description": "User 10, Movie 100 (Fargo)"},
        {"user_id": 50, "movie_id": 200, "description": "User 50, Movie 200 (The Shining)"},
        {"user_id": 100, "movie_id": 300, "description": "User 100, Movie 300 (Air Force One)"},
        {"user_id": 200, "movie_id": 400, "description": "User 200, Movie 400 (Erin Brockovich)"},
        {"user_id": 300, "movie_id": 500, "description": "User 300, Movie 500 (Mrs. Doubtfire)"},
        {"user_id": 400, "movie_id": 600, "description": "User 400, Movie 600 (Blade Runner)"},
        {"user_id": 500, "movie_id": 700, "description": "User 500, Movie 700 (Philadelphia)"},
        {"user_id": 600, "movie_id": 800, "description": "User 600, Movie 800 (Desperado)"},
    ]
    
    print("Running predictions...")
    print("-" * 80)
    print()
    
    successful = 0
    failed = 0
    total_latency = 0
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            # Prepare input - inference expects lists for batch predictions
            input_data = {
                "user_ids": [test_case["user_id"]],
                "movie_ids": [test_case["movie_id"]]
            }
            
            # Invoke endpoint and measure latency
            start_time = time.time()
            
            response = runtime.invoke_endpoint(
                EndpointName=endpoint_name,
                ContentType='application/json',
                Body=json.dumps(input_data)
            )
            
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            total_latency += latency_ms
            
            # Parse response - get first prediction from list
            result = json.loads(response['Body'].read().decode())
            predictions = result.get('predictions', [])
            prediction = predictions[0] if predictions else None
            
            # Display result
            print(f"Test {i:2d}: {test_case['description']}")
            print(f"         Predicted Rating: {prediction:.3f} / 5.0")
            print(f"         Latency: {latency_ms:.1f}ms")
            
            # Check latency
            if latency_ms < 500:
                print(f"         ✅ Latency meets target (< 500ms)")
            elif latency_ms < 1000:
                print(f"         ⚠️  Latency acceptable (< 1000ms)")
            else:
                print(f"         🚨 Latency exceeds threshold (> 1000ms)")
            
            print()
            successful += 1
            
            # Small delay between requests
            time.sleep(0.5)
            
        except Exception as e:
            print(f"Test {i:2d}: {test_case['description']}")
            print(f"         ❌ Error: {e}")
            print()
            failed += 1
    
    # Summary
    print("-" * 80)
    print("SUMMARY")
    print("-" * 80)
    print()
    print(f"Total Tests: {len(test_cases)}")
    print(f"Successful: {successful} ✅")
    print(f"Failed: {failed} {'❌' if failed > 0 else ''}")
    
    if successful > 0:
        avg_latency = total_latency / successful
        print(f"Average Latency: {avg_latency:.1f}ms")
        
        if avg_latency < 500:
            print(f"✅ Average latency meets target (< 500ms)")
        elif avg_latency < 1000:
            print(f"⚠️  Average latency acceptable (< 1000ms)")
        else:
            print(f"🚨 Average latency exceeds threshold (> 1000ms)")
    
    error_rate = (failed / len(test_cases)) * 100
    print(f"Error Rate: {error_rate:.1f}%")
    
    if error_rate == 0:
        print(f"✅ No errors")
    elif error_rate < 5:
        print(f"✅ Error rate within threshold (< 5%)")
    else:
        print(f"🚨 Error rate exceeds threshold (> 5%)")
    
    print()
    print("-" * 80)
    print("NEXT STEPS")
    print("-" * 80)
    print()
    print("1. View metrics in CloudWatch dashboard:")
    print("   https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:")
    print()
    print("2. Check CloudWatch alarms:")
    print("   https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#alarmsV2:")
    print()
    print("3. Subscribe to email alerts:")
    print("   https://console.aws.amazon.com/sns/v3/home?region=us-east-1#/topics")
    print("   Topic: MovieLensEndpointAlarms")
    print()
    print("4. Monitor real-time metrics:")
    print("   python monitor_endpoint_metrics.py")
    print()
    print("=" * 80)


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test MovieLens endpoint predictions')
    parser.add_argument(
        '--endpoint-name',
        type=str,
        help='Endpoint name (auto-detected if not provided)'
    )
    
    args = parser.parse_args()
    
    test_endpoint(args.endpoint_name)


if __name__ == "__main__":
    main()
