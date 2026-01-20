#!/usr/bin/env python3
"""
Test predictions on the deployed MovieLens endpoint.
Run this after the pipeline completes successfully.
"""

import boto3
import json
import sys

def test_endpoint():
    """Test the MovieLens recommendation endpoint."""
    
    endpoint_name = 'movielens-endpoint'
    region = 'us-east-1'
    
    print("\n" + "="*70)
    print("TESTING MOVIELENS ENDPOINT")
    print("="*70)
    print(f"Endpoint: {endpoint_name}")
    print(f"Region: {region}\n")
    
    try:
        # Create SageMaker runtime client
        runtime = boto3.client('sagemaker-runtime', region_name=region)
        
        # Test cases
        test_cases = [
            {'userId': 1, 'movieId': 10, 'description': 'User 1, Movie 10'},
            {'userId': 1, 'movieId': 50, 'description': 'User 1, Movie 50'},
            {'userId': 5, 'movieId': 10, 'description': 'User 5, Movie 10'},
            {'userId': 10, 'movieId': 100, 'description': 'User 10, Movie 100'},
        ]
        
        print("Running test predictions...\n")
        
        success_count = 0
        for i, test_case in enumerate(test_cases, 1):
            try:
                # Prepare payload
                payload = json.dumps({
                    'userId': test_case['userId'],
                    'movieId': test_case['movieId']
                })
                
                # Invoke endpoint
                response = runtime.invoke_endpoint(
                    EndpointName=endpoint_name,
                    ContentType='application/json',
                    Body=payload
                )
                
                # Parse result
                result = json.loads(response['Body'].read())
                rating = result.get('rating', 'N/A')
                
                print(f"Test {i}: {test_case['description']}")
                print(f"  Input: userId={test_case['userId']}, movieId={test_case['movieId']}")
                print(f"  Predicted rating: {rating:.2f}")
                print(f"  Status: SUCCESS")
                print()
                
                success_count += 1
                
            except Exception as e:
                print(f"Test {i}: {test_case['description']}")
                print(f"  Status: FAILED")
                print(f"  Error: {str(e)}")
                print()
        
        # Summary
        print("="*70)
        print(f"RESULTS: {success_count}/{len(test_cases)} tests passed")
        
        if success_count == len(test_cases):
            print("\n*** ALL TESTS PASSED! ***")
            print("The endpoint is working correctly!")
            print("\nYou can now:")
            print("1. Integrate this endpoint into your application")
            print("2. Review CloudWatch metrics")
            print("3. Test with your own user/movie IDs")
        else:
            print("\n*** SOME TESTS FAILED ***")
            print("Check the errors above for details")
        
        print("="*70)
        print()
        
        return success_count == len(test_cases)
        
    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nPossible causes:")
        print("1. Endpoint not yet deployed (wait for pipeline to complete)")
        print("2. Endpoint name incorrect")
        print("3. AWS credentials not configured")
        print("4. Insufficient permissions")
        print("\nTo check endpoint status:")
        print("  aws sagemaker describe-endpoint --endpoint-name movielens-endpoint --region us-east-1")
        print()
        return False

def check_endpoint_status():
    """Check if the endpoint exists and is ready."""
    
    endpoint_name = 'movielens-endpoint'
    region = 'us-east-1'
    
    try:
        sagemaker = boto3.client('sagemaker', region_name=region)
        response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
        
        status = response['EndpointStatus']
        print(f"\nEndpoint Status: {status}")
        
        if status == 'InService':
            print("Endpoint is ready for predictions!")
            return True
        elif status == 'Creating':
            print("Endpoint is still being created. Wait a few minutes and try again.")
            return False
        elif status == 'Failed':
            print("Endpoint creation failed. Check CloudWatch logs.")
            return False
        else:
            print(f"Endpoint is in {status} state.")
            return False
            
    except sagemaker.exceptions.ClientError as e:
        if 'Could not find endpoint' in str(e):
            print("\nEndpoint not found. The pipeline may not have completed yet.")
            print("Wait for the pipeline to finish, then try again.")
        else:
            print(f"\nError checking endpoint: {e}")
        return False
    except Exception as e:
        print(f"\nError: {e}")
        return False

if __name__ == "__main__":
    # First check if endpoint exists
    if check_endpoint_status():
        # Run tests
        success = test_endpoint()
        sys.exit(0 if success else 1)
    else:
        print("\nCannot run tests until endpoint is ready.")
        sys.exit(1)
