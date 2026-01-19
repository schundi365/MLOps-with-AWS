"""
Lambda Functions Deployment Script for MovieLens Recommendation System

This script packages and deploys Lambda functions:
- Model evaluation Lambda
- Monitoring setup Lambda

Requirements: 10.1, 8.1
"""

import boto3
import os
import zipfile
import tempfile
import shutil
import time
from typing import Optional
from botocore.exceptions import ClientError


class LambdaDeployment:
    """Manages Lambda function deployment"""
    
    def __init__(self, region: str = 'us-east-1'):
        """
        Initialize Lambda deployment
        
        Args:
            region: AWS region
        """
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        
    def package_lambda_function(
        self,
        source_file: str,
        dependencies: list = None,
        output_zip: str = None
    ) -> str:
        """
        Package Lambda function with dependencies
        
        Args:
            source_file: Path to the Lambda function source file
            dependencies: List of dependency packages to include
            output_zip: Output zip file path (optional)
            
        Returns:
            Path to the created zip file
        """
        if output_zip is None:
            output_zip = tempfile.mktemp(suffix='.zip')
        
        # Create temporary directory for packaging
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Copy source file
            source_filename = os.path.basename(source_file)
            shutil.copy(source_file, os.path.join(temp_dir, source_filename))
            
            # Install dependencies if specified
            if dependencies:
                import subprocess
                subprocess.check_call([
                    'pip', 'install',
                    '--target', temp_dir,
                    '--upgrade'
                ] + dependencies)
            
            # Create zip file
            with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, arcname)
            
            print(f"[OK] Packaged Lambda function: {output_zip}")
            return output_zip
            
        finally:
            # Clean up temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def deploy_lambda_function(
        self,
        function_name: str,
        role_arn: str,
        zip_file_path: str,
        handler: str,
        runtime: str = 'python3.10',
        timeout: int = 300,
        memory_size: int = 512,
        environment_variables: dict = None
    ) -> Optional[str]:
        """
        Deploy Lambda function
        
        Args:
            function_name: Name of the Lambda function
            role_arn: IAM role ARN for Lambda execution
            zip_file_path: Path to the deployment package zip file
            handler: Handler function (e.g., 'lambda_evaluation.lambda_handler')
            runtime: Python runtime version
            timeout: Function timeout in seconds
            memory_size: Memory allocation in MB
            environment_variables: Environment variables for the function
            
        Returns:
            Function ARN if successful, None otherwise
        """
        try:
            # Read zip file
            with open(zip_file_path, 'rb') as f:
                zip_content = f.read()
            
            # Check if function exists
            try:
                self.lambda_client.get_function(FunctionName=function_name)
                # Function exists, update it
                response = self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=zip_content
                )
                
                # Wait for the code update to complete before updating configuration
                print(f"  Waiting for code update to complete...")
                waiter = self.lambda_client.get_waiter('function_updated')
                waiter.wait(
                    FunctionName=function_name,
                    WaiterConfig={'Delay': 2, 'MaxAttempts': 30}
                )
                
                # Update configuration
                config_response = self.lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Role=role_arn,
                    Handler=handler,
                    Runtime=runtime,
                    Timeout=timeout,
                    MemorySize=memory_size,
                    Environment={'Variables': environment_variables or {}}
                )
                
                # Wait for configuration update to complete
                print(f"  Waiting for configuration update to complete...")
                waiter.wait(
                    FunctionName=function_name,
                    WaiterConfig={'Delay': 2, 'MaxAttempts': 30}
                )
                
                print(f"[OK] Updated Lambda function: {function_name}")
                return response['FunctionArn']
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    # Function doesn't exist, create it
                    response = self.lambda_client.create_function(
                        FunctionName=function_name,
                        Runtime=runtime,
                        Role=role_arn,
                        Handler=handler,
                        Code={'ZipFile': zip_content},
                        Timeout=timeout,
                        MemorySize=memory_size,
                        Environment={'Variables': environment_variables or {}},
                        Description=f'MovieLens recommendation system - {function_name}'
                    )
                    
                    # Wait for function to be active
                    print(f"  Waiting for function creation to complete...")
                    waiter = self.lambda_client.get_waiter('function_active')
                    waiter.wait(
                        FunctionName=function_name,
                        WaiterConfig={'Delay': 2, 'MaxAttempts': 30}
                    )
                    
                    print(f"[OK] Created Lambda function: {function_name}")
                    return response['FunctionArn']
                else:
                    raise
                    
        except ClientError as e:
            print(f"[X] Error deploying Lambda function {function_name}: {e}")
            return None
    
    def deploy_evaluation_lambda(
        self,
        function_name: str,
        role_arn: str,
        source_file: str,
        bucket_name: str
    ) -> Optional[str]:
        """
        Deploy model evaluation Lambda function
        
        Args:
            function_name: Name for the Lambda function
            role_arn: IAM role ARN
            source_file: Path to lambda_evaluation.py
            bucket_name: S3 bucket name
            
        Returns:
            Function ARN if successful
        """
        print(f"\n--- Deploying Evaluation Lambda ---")
        
        # Package function with dependencies
        dependencies = ['boto3', 'numpy']
        zip_file = self.package_lambda_function(
            source_file,
            dependencies,
            output_zip=os.path.join(tempfile.gettempdir(), f'{function_name}.zip')
        )
        
        # Deploy function
        environment_vars = {
            'BUCKET_NAME': bucket_name
        }
        
        function_arn = self.deploy_lambda_function(
            function_name=function_name,
            role_arn=role_arn,
            zip_file_path=zip_file,
            handler='lambda_evaluation.lambda_handler',
            runtime='python3.10',
            timeout=300,
            memory_size=512,
            environment_variables=environment_vars
        )
        
        # Clean up zip file
        if os.path.exists(zip_file):
            os.remove(zip_file)
        
        return function_arn
    
    def deploy_monitoring_lambda(
        self,
        function_name: str,
        role_arn: str,
        source_file: str,
        bucket_name: str
    ) -> Optional[str]:
        """
        Deploy monitoring setup Lambda function
        
        Args:
            function_name: Name for the Lambda function
            role_arn: IAM role ARN
            source_file: Path to monitoring.py
            bucket_name: S3 bucket name
            
        Returns:
            Function ARN if successful
        """
        print(f"\n--- Deploying Monitoring Lambda ---")
        
        # Package function with dependencies
        dependencies = ['boto3']
        zip_file = self.package_lambda_function(
            source_file,
            dependencies,
            output_zip=os.path.join(tempfile.gettempdir(), f'{function_name}.zip')
        )
        
        # Deploy function
        environment_vars = {
            'BUCKET_NAME': bucket_name
        }
        
        function_arn = self.deploy_lambda_function(
            function_name=function_name,
            role_arn=role_arn,
            zip_file_path=zip_file,
            handler='monitoring.lambda_handler',
            runtime='python3.10',
            timeout=60,
            memory_size=256,
            environment_variables=environment_vars
        )
        
        # Clean up zip file
        if os.path.exists(zip_file):
            os.remove(zip_file)
        
        return function_arn
    
    def deploy_all_lambda_functions(
        self,
        bucket_name: str,
        evaluation_role_arn: str,
        monitoring_role_arn: str,
        evaluation_source: str = 'src/lambda_evaluation.py',
        monitoring_source: str = 'src/monitoring.py'
    ) -> dict:
        """
        Deploy all Lambda functions for the ML pipeline
        
        Args:
            bucket_name: S3 bucket name
            evaluation_role_arn: IAM role ARN for evaluation Lambda
            monitoring_role_arn: IAM role ARN for monitoring Lambda
            evaluation_source: Path to evaluation Lambda source
            monitoring_source: Path to monitoring Lambda source
            
        Returns:
            Dictionary mapping function names to ARNs
        """
        print(f"\n=== Deploying Lambda Functions ===\n")
        
        functions = {}
        
        # Deploy evaluation Lambda
        eval_arn = self.deploy_evaluation_lambda(
            function_name='movielens-model-evaluation',
            role_arn=evaluation_role_arn,
            source_file=evaluation_source,
            bucket_name=bucket_name
        )
        if eval_arn:
            functions['evaluation'] = eval_arn
        
        # Deploy monitoring Lambda
        monitor_arn = self.deploy_monitoring_lambda(
            function_name='movielens-monitoring-setup',
            role_arn=monitoring_role_arn,
            source_file=monitoring_source,
            bucket_name=bucket_name
        )
        if monitor_arn:
            functions['monitoring'] = monitor_arn
        
        print(f"\n[OK] Successfully deployed {len(functions)} Lambda functions")
        return functions


def main():
    """Main function for standalone execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy Lambda functions for MovieLens recommendation system')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--bucket-name', required=True, help='S3 bucket name')
    parser.add_argument('--evaluation-role-arn', required=True, help='Evaluation Lambda role ARN')
    parser.add_argument('--monitoring-role-arn', required=True, help='Monitoring Lambda role ARN')
    parser.add_argument('--evaluation-source', default='src/lambda_evaluation.py', help='Path to evaluation Lambda source')
    parser.add_argument('--monitoring-source', default='src/monitoring.py', help='Path to monitoring Lambda source')
    
    args = parser.parse_args()
    
    deployment = LambdaDeployment(args.region)
    functions = deployment.deploy_all_lambda_functions(
        bucket_name=args.bucket_name,
        evaluation_role_arn=args.evaluation_role_arn,
        monitoring_role_arn=args.monitoring_role_arn,
        evaluation_source=args.evaluation_source,
        monitoring_source=args.monitoring_source
    )
    
    print("\n=== Lambda Function ARNs ===")
    for func_type, arn in functions.items():
        print(f"{func_type}: {arn}")
    
    exit(0 if len(functions) == 2 else 1)


if __name__ == '__main__':
    main()
