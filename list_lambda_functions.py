"""
List all Lambda functions to find the monitoring function name.
"""

import boto3

def list_lambda_functions():
    """List all Lambda functions."""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("\n" + "="*70)
    print("LAMBDA FUNCTIONS")
    print("="*70 + "\n")
    
    try:
        response = lambda_client.list_functions()
        
        movielens_functions = [
            f for f in response['Functions']
            if 'movielens' in f['FunctionName'].lower() or 'MovieLens' in f['FunctionName']
        ]
        
        if not movielens_functions:
            print("No MovieLens Lambda functions found")
            print("\nAll functions:")
            for func in response['Functions']:
                print(f"  - {func['FunctionName']}")
        else:
            print("MovieLens Lambda functions:")
            for func in movielens_functions:
                print(f"\nFunction: {func['FunctionName']}")
                print(f"  Runtime: {func['Runtime']}")
                print(f"  Handler: {func['Handler']}")
                print(f"  Last Modified: {func['LastModified']}")
        
    except Exception as e:
        print(f"Error listing functions: {e}")

if __name__ == '__main__':
    list_lambda_functions()
