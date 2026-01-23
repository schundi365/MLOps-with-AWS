"""
Redeploy monitoring Lambda function with lambda_handler.
"""

import boto3
import zipfile
import io
import os

def redeploy_monitoring_lambda():
    """Redeploy the monitoring Lambda function."""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    print("\n" + "="*70)
    print("REDEPLOYING MONITORING LAMBDA FUNCTION")
    print("="*70 + "\n")
    
    # Create deployment package
    print("1. Creating deployment package...")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add monitoring.py
        zip_file.write('src/monitoring.py', 'monitoring.py')
        print("   ✓ Added monitoring.py")
    
    zip_buffer.seek(0)
    zip_content = zip_buffer.read()
    
    print(f"   Package size: {len(zip_content)} bytes")
    
    # Update Lambda function code
    print("\n2. Updating Lambda function code...")
    
    function_name = 'movielens-monitoring-setup'
    
    try:
        response = lambda_client.update_function_code(
            FunctionName=function_name,
            ZipFile=zip_content
        )
        
        print(f"   ✓ Function updated: {function_name}")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Runtime: {response['Runtime']}")
        print(f"   Handler: {response['Handler']}")
        print(f"   Last Modified: {response['LastModified']}")
        
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"   ✗ Function not found: {function_name}")
        print("   The function may need to be created first")
        return False
    except Exception as e:
        print(f"   ✗ Error updating function: {e}")
        return False
    
    print("\n" + "="*70)
    print("✓ MONITORING LAMBDA FUNCTION REDEPLOYED")
    print("="*70)
    print()
    print("The monitoring Lambda now has the lambda_handler function.")
    print()
    print("Next steps:")
    print("  1. The current pipeline execution should now proceed")
    print("  2. Monitor the execution to verify it completes")
    print()
    
    return True

if __name__ == '__main__':
    success = redeploy_monitoring_lambda()
    exit(0 if success else 1)
