#!/usr/bin/env python3
"""Check what Lambda functions exist."""

import boto3

def main():
    region = 'us-east-1'
    lambda_client = boto3.client('lambda', region_name=region)
    
    print("\n" + "="*70)
    print("LAMBDA FUNCTIONS CHECK")
    print("="*70)
    print()
    
    # List all functions
    response = lambda_client.list_functions()
    
    movielens_functions = [f for f in response['Functions'] 
                          if 'movielens' in f['FunctionName'].lower()]
    
    if movielens_functions:
        print(f"Found {len(movielens_functions)} MovieLens Lambda function(s):")
        print()
        for func in movielens_functions:
            print(f"  Name: {func['FunctionName']}")
            print(f"  ARN: {func['FunctionArn']}")
            print(f"  Runtime: {func['Runtime']}")
            print(f"  Handler: {func['Handler']}")
            print()
    else:
        print("No MovieLens Lambda functions found!")
        print()
        print("Expected functions:")
        print("  - movielens-evaluation")
        print("  - movielens-monitoring-setup")
        print()
    
    print("="*70)

if __name__ == "__main__":
    main()
