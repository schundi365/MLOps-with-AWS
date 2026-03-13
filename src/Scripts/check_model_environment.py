"""
Check if the model has the correct environment variables.
"""

import boto3

def check_model_environment():
    """Check the environment variables on the deployed model."""
    
    sagemaker_client = boto3.client('sagemaker', region_name='us-east-1')
    
    # Get the model name from the latest execution
    model_name = 'movielens-model-20260122-162230-4567'
    
    print(f"\n{'='*70}")
    print(f"CHECKING MODEL CONFIGURATION: {model_name}")
    print(f"{'='*70}\n")
    
    try:
        response = sagemaker_client.describe_model(ModelName=model_name)
        
        print("Model Details:")
        print(f"  Model Name: {response['ModelName']}")
        print(f"  Creation Time: {response['CreationTime']}")
        print(f"  Execution Role: {response['ExecutionRoleArn']}")
        
        print("\nPrimary Container:")
        container = response['PrimaryContainer']
        print(f"  Image: {container['Image']}")
        print(f"  Model Data: {container.get('ModelDataUrl', 'N/A')}")
        
        if 'Environment' in container:
            print("\n  Environment Variables:")
            for key, value in container['Environment'].items():
                print(f"    {key}: {value}")
        else:
            print("\n  ⚠ NO ENVIRONMENT VARIABLES SET!")
            print("  This is why the default handler is being used.")
        
        print(f"\n{'='*70}\n")
        
    except sagemaker_client.exceptions.ClientError as e:
        if 'Could not find model' in str(e):
            print(f"Model not found: {model_name}")
        else:
            print(f"Error: {e}")

if __name__ == '__main__':
    check_model_environment()
