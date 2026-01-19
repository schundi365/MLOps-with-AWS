"""
AWS Lambda function for model evaluation.

This Lambda function evaluates a trained collaborative filtering model on test data.
It loads test data from S3, invokes a SageMaker endpoint for predictions, calculates
evaluation metrics (RMSE and MAE), and stores the results back to S3.

Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
"""

import json
import logging
import os
from typing import Dict, Any, List
import io

import boto3
import pandas as pd
import numpy as np


# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
sagemaker_runtime = boto3.client('sagemaker-runtime')


def calculate_rmse(predictions: List[float], actuals: List[float]) -> float:
    """
    Calculate Root Mean Square Error.
    
    Args:
        predictions: List of predicted ratings
        actuals: List of actual ratings
    
    Returns:
        RMSE value
    
    Validates: Requirements 10.2
    """
    predictions_array = np.array(predictions)
    actuals_array = np.array(actuals)
    
    mse = np.mean((predictions_array - actuals_array) ** 2)
    rmse = np.sqrt(mse)
    
    return float(rmse)


def calculate_mae(predictions: List[float], actuals: List[float]) -> float:
    """
    Calculate Mean Absolute Error.
    
    Args:
        predictions: List of predicted ratings
        actuals: List of actual ratings
    
    Returns:
        MAE value
    
    Validates: Requirements 10.2
    """
    predictions_array = np.array(predictions)
    actuals_array = np.array(actuals)
    
    mae = np.mean(np.abs(predictions_array - actuals_array))
    
    return float(mae)


def load_test_data_from_s3(bucket: str, key: str) -> pd.DataFrame:
    """
    Load test data from S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key (path to test data CSV)
    
    Returns:
        DataFrame with test data
    
    Validates: Requirements 10.1
    """
    logger.info(f"Loading test data from s3://{bucket}/{key}")
    
    try:
        # Get object from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        
        # Read CSV data
        csv_content = response['Body'].read()
        test_data = pd.read_csv(io.BytesIO(csv_content))
        
        logger.info(f"Loaded {len(test_data)} test samples")
        
        # Validate required columns
        required_columns = ['userId', 'movieId', 'rating']
        missing_columns = [col for col in required_columns if col not in test_data.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns in test data: {missing_columns}")
        
        return test_data
        
    except Exception as e:
        logger.error(f"Error loading test data from S3: {str(e)}")
        raise


def invoke_endpoint_for_predictions(endpoint_name: str, user_ids: List[int], 
                                    movie_ids: List[int]) -> List[float]:
    """
    Invoke SageMaker endpoint to get predictions.
    
    Args:
        endpoint_name: Name of the SageMaker endpoint
        user_ids: List of user IDs
        movie_ids: List of movie IDs
    
    Returns:
        List of predicted ratings
    
    Validates: Requirements 10.1
    """
    logger.info(f"Invoking endpoint {endpoint_name} for {len(user_ids)} predictions")
    
    try:
        # Prepare request payload
        payload = {
            'user_ids': user_ids,
            'movie_ids': movie_ids
        }
        
        # Invoke endpoint
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=endpoint_name,
            ContentType='application/json',
            Body=json.dumps(payload)
        )
        
        # Parse response
        result = json.loads(response['Body'].read().decode())
        predictions = result['predictions']
        
        logger.info(f"Received {len(predictions)} predictions from endpoint")
        
        return predictions
        
    except Exception as e:
        logger.error(f"Error invoking endpoint: {str(e)}")
        raise


def store_metrics_to_s3(bucket: str, key: str, metrics: Dict[str, Any]) -> None:
    """
    Store evaluation metrics to S3 as JSON.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key (path to store metrics)
        metrics: Dictionary containing evaluation metrics
    
    Validates: Requirements 10.3
    """
    logger.info(f"Storing metrics to s3://{bucket}/{key}")
    
    try:
        # Convert metrics to JSON
        metrics_json = json.dumps(metrics, indent=2)
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=metrics_json,
            ContentType='application/json'
        )
        
        logger.info("Metrics stored successfully")
        
    except Exception as e:
        logger.error(f"Error storing metrics to S3: {str(e)}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler function for model evaluation.
    
    This function orchestrates the evaluation process:
    1. Load test data from S3
    2. Invoke SageMaker endpoint for predictions
    3. Calculate RMSE and MAE metrics
    4. Count test samples
    5. Store metrics to S3
    6. Return metrics dictionary
    
    Expected event structure:
    {
        "test_data_bucket": "bucket-name",
        "test_data_key": "processed-data/test.csv",
        "endpoint_name": "movielens-endpoint",
        "metrics_bucket": "bucket-name",
        "metrics_key": "metrics/evaluation_results.json"
    }
    
    Args:
        event: Lambda event containing S3 paths and endpoint name
        context: Lambda context object
    
    Returns:
        Dictionary with evaluation metrics (rmse, mae, test_samples)
    
    Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5
    """
    logger.info("Starting model evaluation")
    logger.info(f"Event: {json.dumps(event)}")
    
    try:
        # Extract parameters from event
        test_data_bucket = event.get('test_data_bucket')
        test_data_key = event.get('test_data_key')
        endpoint_name = event.get('endpoint_name')
        metrics_bucket = event.get('metrics_bucket')
        metrics_key = event.get('metrics_key')
        
        # Validate required parameters
        if not all([test_data_bucket, test_data_key, endpoint_name, metrics_bucket, metrics_key]):
            raise ValueError("Missing required parameters in event")
        
        # Load test data from S3
        test_data = load_test_data_from_s3(test_data_bucket, test_data_key)
        
        # Count test samples
        test_samples = len(test_data)
        logger.info(f"Test samples: {test_samples}")
        
        # Extract user IDs, movie IDs, and actual ratings
        user_ids = test_data['userId'].tolist()
        movie_ids = test_data['movieId'].tolist()
        actual_ratings = test_data['rating'].tolist()
        
        # Invoke endpoint for predictions
        # Note: For large test sets, we might want to batch this
        # For now, we'll invoke with all data at once
        predictions = invoke_endpoint_for_predictions(endpoint_name, user_ids, movie_ids)
        
        # Validate prediction count matches test samples
        if len(predictions) != test_samples:
            raise ValueError(
                f"Prediction count ({len(predictions)}) does not match test samples ({test_samples})"
            )
        
        # Calculate RMSE
        rmse = calculate_rmse(predictions, actual_ratings)
        logger.info(f"RMSE: {rmse:.4f}")
        
        # Calculate MAE
        mae = calculate_mae(predictions, actual_ratings)
        logger.info(f"MAE: {mae:.4f}")
        
        # Prepare metrics dictionary
        metrics = {
            'rmse': rmse,
            'mae': mae,
            'test_samples': test_samples
        }
        
        # Store metrics to S3
        store_metrics_to_s3(metrics_bucket, metrics_key, metrics)
        
        # Return metrics for Step Functions
        logger.info("Model evaluation completed successfully")
        return metrics
        
    except Exception as e:
        logger.error(f"Error during model evaluation: {str(e)}")
        raise


# For local testing
if __name__ == '__main__':
    # Example event for local testing
    test_event = {
        'test_data_bucket': 'movielens-recommendation-bucket',
        'test_data_key': 'processed-data/test.csv',
        'endpoint_name': 'movielens-endpoint',
        'metrics_bucket': 'movielens-recommendation-bucket',
        'metrics_key': 'metrics/evaluation_results.json'
    }
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.function_name = 'model-evaluation'
            self.memory_limit_in_mb = 512
            self.invoked_function_arn = 'arn:aws:lambda:us-east-1:123456789012:function:model-evaluation'
            self.aws_request_id = 'test-request-id'
    
    result = lambda_handler(test_event, MockContext())
    print(json.dumps(result, indent=2))
