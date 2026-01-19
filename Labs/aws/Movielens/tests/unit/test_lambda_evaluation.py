"""
Unit tests for Lambda evaluation function.

Tests cover:
- Small test dataset processing
- S3 read/write operations
- Error handling for missing data

Validates: Requirements 10.1, 10.2, 10.3, 10.5
"""

import json
import io
from unittest.mock import Mock, patch, MagicMock
import pytest
import pandas as pd
import numpy as np

from src.lambda_evaluation import (
    lambda_handler,
    load_test_data_from_s3,
    invoke_endpoint_for_predictions,
    store_metrics_to_s3,
    calculate_rmse,
    calculate_mae
)


class TestLambdaHandlerWithSmallDataset:
    """Test lambda_handler with small test dataset"""
    
    @patch('src.lambda_evaluation.s3_client')
    @patch('src.lambda_evaluation.sagemaker_runtime')
    def test_lambda_handler_small_dataset(self, mock_sagemaker, mock_s3):
        """Test lambda handler with small test dataset"""
        # Create small test dataset
        test_data = pd.DataFrame({
            'userId': [1, 2, 3, 4, 5],
            'movieId': [10, 20, 30, 40, 50],
            'rating': [4.0, 3.5, 5.0, 2.5, 4.5]
        })
        
        # Mock S3 get_object to return test data
        csv_buffer = io.BytesIO()
        test_data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            'Body': csv_buffer
        }
        
        # Mock SageMaker endpoint response
        predictions = [4.1, 3.4, 4.9, 2.6, 4.4]
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'predictions': predictions
        }).encode()
        
        mock_sagemaker.invoke_endpoint.return_value = {
            'Body': mock_response
        }
        
        # Mock S3 put_object
        mock_s3.put_object.return_value = {}
        
        # Create event
        event = {
            'test_data_bucket': 'test-bucket',
            'test_data_key': 'test.csv',
            'endpoint_name': 'test-endpoint',
            'metrics_bucket': 'test-bucket',
            'metrics_key': 'metrics.json'
        }
        
        # Execute lambda handler
        result = lambda_handler(event, None)
        
        # Verify results
        assert 'rmse' in result
        assert 'mae' in result
        assert 'test_samples' in result
        assert result['test_samples'] == 5
        assert isinstance(result['rmse'], float)
        assert isinstance(result['mae'], float)
        assert result['rmse'] > 0
        assert result['mae'] > 0
        
        # Verify S3 get_object was called
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test.csv'
        )
        
        # Verify endpoint was invoked
        mock_sagemaker.invoke_endpoint.assert_called_once()
        
        # Verify metrics were stored to S3
        mock_s3.put_object.assert_called_once()
        put_call_args = mock_s3.put_object.call_args
        assert put_call_args[1]['Bucket'] == 'test-bucket'
        assert put_call_args[1]['Key'] == 'metrics.json'
        assert put_call_args[1]['ContentType'] == 'application/json'
    
    @patch('src.lambda_evaluation.s3_client')
    @patch('src.lambda_evaluation.sagemaker_runtime')
    def test_lambda_handler_single_sample(self, mock_sagemaker, mock_s3):
        """Test lambda handler with single test sample"""
        # Create single sample dataset
        test_data = pd.DataFrame({
            'userId': [1],
            'movieId': [10],
            'rating': [4.0]
        })
        
        # Mock S3 get_object
        csv_buffer = io.BytesIO()
        test_data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            'Body': csv_buffer
        }
        
        # Mock SageMaker endpoint response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'predictions': [4.1]
        }).encode()
        
        mock_sagemaker.invoke_endpoint.return_value = {
            'Body': mock_response
        }
        
        # Mock S3 put_object
        mock_s3.put_object.return_value = {}
        
        # Create event
        event = {
            'test_data_bucket': 'test-bucket',
            'test_data_key': 'test.csv',
            'endpoint_name': 'test-endpoint',
            'metrics_bucket': 'test-bucket',
            'metrics_key': 'metrics.json'
        }
        
        # Execute lambda handler
        result = lambda_handler(event, None)
        
        # Verify results
        assert result['test_samples'] == 1
        assert result['rmse'] > 0
        assert result['mae'] > 0


class TestS3ReadOperations:
    """Test S3 read operations"""
    
    @patch('src.lambda_evaluation.s3_client')
    def test_load_test_data_from_s3_success(self, mock_s3):
        """Test successful loading of test data from S3"""
        # Create test data
        test_data = pd.DataFrame({
            'userId': [1, 2, 3],
            'movieId': [10, 20, 30],
            'rating': [4.0, 3.5, 5.0]
        })
        
        # Mock S3 response
        csv_buffer = io.BytesIO()
        test_data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            'Body': csv_buffer
        }
        
        # Load data
        result = load_test_data_from_s3('test-bucket', 'test.csv')
        
        # Verify
        assert len(result) == 3
        assert list(result.columns) == ['userId', 'movieId', 'rating']
        assert result['userId'].tolist() == [1, 2, 3]
        assert result['movieId'].tolist() == [10, 20, 30]
        assert result['rating'].tolist() == [4.0, 3.5, 5.0]
        
        # Verify S3 was called correctly
        mock_s3.get_object.assert_called_once_with(
            Bucket='test-bucket',
            Key='test.csv'
        )
    
    @patch('src.lambda_evaluation.s3_client')
    def test_load_test_data_with_additional_columns(self, mock_s3):
        """Test loading data with additional columns beyond required ones"""
        # Create test data with extra columns
        test_data = pd.DataFrame({
            'userId': [1, 2],
            'movieId': [10, 20],
            'rating': [4.0, 3.5],
            'timestamp': [1234567890, 1234567891],
            'genres': ['Action', 'Comedy']
        })
        
        # Mock S3 response
        csv_buffer = io.BytesIO()
        test_data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            'Body': csv_buffer
        }
        
        # Load data
        result = load_test_data_from_s3('test-bucket', 'test.csv')
        
        # Verify all columns are preserved
        assert len(result) == 2
        assert 'userId' in result.columns
        assert 'movieId' in result.columns
        assert 'rating' in result.columns
        assert 'timestamp' in result.columns
        assert 'genres' in result.columns


class TestS3WriteOperations:
    """Test S3 write operations"""
    
    @patch('src.lambda_evaluation.s3_client')
    def test_store_metrics_to_s3_success(self, mock_s3):
        """Test successful storing of metrics to S3"""
        # Mock S3 put_object
        mock_s3.put_object.return_value = {}
        
        # Prepare metrics
        metrics = {
            'rmse': 0.85,
            'mae': 0.65,
            'test_samples': 1000
        }
        
        # Store metrics
        store_metrics_to_s3('test-bucket', 'metrics/results.json', metrics)
        
        # Verify S3 put_object was called
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args
        
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert call_args[1]['Key'] == 'metrics/results.json'
        assert call_args[1]['ContentType'] == 'application/json'
        
        # Verify JSON content
        stored_json = call_args[1]['Body']
        stored_metrics = json.loads(stored_json)
        assert stored_metrics == metrics
    
    @patch('src.lambda_evaluation.s3_client')
    def test_store_metrics_formats_json_correctly(self, mock_s3):
        """Test that metrics are formatted as valid JSON"""
        mock_s3.put_object.return_value = {}
        
        metrics = {
            'rmse': 0.87654321,
            'mae': 0.65432109,
            'test_samples': 2500000
        }
        
        store_metrics_to_s3('test-bucket', 'metrics.json', metrics)
        
        # Get the stored JSON
        call_args = mock_s3.put_object.call_args
        stored_json = call_args[1]['Body']
        
        # Verify it's valid JSON
        parsed = json.loads(stored_json)
        assert parsed['rmse'] == metrics['rmse']
        assert parsed['mae'] == metrics['mae']
        assert parsed['test_samples'] == metrics['test_samples']


class TestErrorHandlingMissingData:
    """Test error handling for missing data scenarios"""
    
    @patch('src.lambda_evaluation.s3_client')
    def test_load_test_data_missing_bucket(self, mock_s3):
        """Test error handling when S3 bucket doesn't exist"""
        # Mock S3 to raise NoSuchBucket error
        from botocore.exceptions import ClientError
        
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'The specified bucket does not exist'}},
            'GetObject'
        )
        
        # Verify exception is raised
        with pytest.raises(ClientError):
            load_test_data_from_s3('nonexistent-bucket', 'test.csv')
    
    @patch('src.lambda_evaluation.s3_client')
    def test_load_test_data_missing_key(self, mock_s3):
        """Test error handling when S3 key doesn't exist"""
        from botocore.exceptions import ClientError
        
        # Mock S3 to raise NoSuchKey error
        mock_s3.get_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist'}},
            'GetObject'
        )
        
        # Verify exception is raised
        with pytest.raises(ClientError):
            load_test_data_from_s3('test-bucket', 'nonexistent.csv')
    
    @patch('src.lambda_evaluation.s3_client')
    def test_load_test_data_missing_required_columns(self, mock_s3):
        """Test error handling when test data is missing required columns"""
        # Create test data missing 'rating' column
        test_data = pd.DataFrame({
            'userId': [1, 2, 3],
            'movieId': [10, 20, 30]
            # Missing 'rating' column
        })
        
        # Mock S3 response
        csv_buffer = io.BytesIO()
        test_data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            'Body': csv_buffer
        }
        
        # Verify exception is raised
        with pytest.raises(ValueError, match="Missing required columns"):
            load_test_data_from_s3('test-bucket', 'test.csv')
    
    @patch('src.lambda_evaluation.s3_client')
    def test_load_test_data_missing_multiple_columns(self, mock_s3):
        """Test error handling when multiple required columns are missing"""
        # Create test data with only one required column
        test_data = pd.DataFrame({
            'userId': [1, 2, 3]
            # Missing 'movieId' and 'rating' columns
        })
        
        # Mock S3 response
        csv_buffer = io.BytesIO()
        test_data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            'Body': csv_buffer
        }
        
        # Verify exception is raised with both missing columns
        with pytest.raises(ValueError) as exc_info:
            load_test_data_from_s3('test-bucket', 'test.csv')
        
        error_message = str(exc_info.value)
        assert 'movieId' in error_message
        assert 'rating' in error_message
    
    def test_lambda_handler_missing_required_parameters(self):
        """Test error handling when event is missing required parameters"""
        # Event missing endpoint_name
        event = {
            'test_data_bucket': 'test-bucket',
            'test_data_key': 'test.csv',
            # Missing 'endpoint_name'
            'metrics_bucket': 'test-bucket',
            'metrics_key': 'metrics.json'
        }
        
        # Verify exception is raised
        with pytest.raises(ValueError, match="Missing required parameters"):
            lambda_handler(event, None)
    
    def test_lambda_handler_empty_event(self):
        """Test error handling with empty event"""
        event = {}
        
        # Verify exception is raised
        with pytest.raises(ValueError, match="Missing required parameters"):
            lambda_handler(event, None)
    
    @patch('src.lambda_evaluation.s3_client')
    @patch('src.lambda_evaluation.sagemaker_runtime')
    def test_lambda_handler_prediction_count_mismatch(self, mock_sagemaker, mock_s3):
        """Test error handling when prediction count doesn't match test samples"""
        # Create test data with 5 samples
        test_data = pd.DataFrame({
            'userId': [1, 2, 3, 4, 5],
            'movieId': [10, 20, 30, 40, 50],
            'rating': [4.0, 3.5, 5.0, 2.5, 4.5]
        })
        
        # Mock S3 get_object
        csv_buffer = io.BytesIO()
        test_data.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        
        mock_s3.get_object.return_value = {
            'Body': csv_buffer
        }
        
        # Mock SageMaker to return only 3 predictions (mismatch)
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            'predictions': [4.1, 3.4, 4.9]  # Only 3 predictions for 5 samples
        }).encode()
        
        mock_sagemaker.invoke_endpoint.return_value = {
            'Body': mock_response
        }
        
        # Create event
        event = {
            'test_data_bucket': 'test-bucket',
            'test_data_key': 'test.csv',
            'endpoint_name': 'test-endpoint',
            'metrics_bucket': 'test-bucket',
            'metrics_key': 'metrics.json'
        }
        
        # Verify exception is raised
        with pytest.raises(ValueError, match="Prediction count .* does not match test samples"):
            lambda_handler(event, None)
    
    @patch('src.lambda_evaluation.s3_client')
    def test_store_metrics_s3_access_denied(self, mock_s3):
        """Test error handling when S3 access is denied during metrics storage"""
        from botocore.exceptions import ClientError
        
        # Mock S3 to raise AccessDenied error
        mock_s3.put_object.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}},
            'PutObject'
        )
        
        metrics = {'rmse': 0.85, 'mae': 0.65, 'test_samples': 1000}
        
        # Verify exception is raised
        with pytest.raises(ClientError):
            store_metrics_to_s3('test-bucket', 'metrics.json', metrics)
    
    @patch('src.lambda_evaluation.sagemaker_runtime')
    def test_invoke_endpoint_not_found(self, mock_sagemaker):
        """Test error handling when SageMaker endpoint doesn't exist"""
        from botocore.exceptions import ClientError
        
        # Mock SageMaker to raise ValidationException
        mock_sagemaker.invoke_endpoint.side_effect = ClientError(
            {'Error': {'Code': 'ValidationException', 'Message': 'Could not find endpoint'}},
            'InvokeEndpoint'
        )
        
        # Verify exception is raised
        with pytest.raises(ClientError):
            invoke_endpoint_for_predictions('nonexistent-endpoint', [1, 2], [10, 20])
    
    @patch('src.lambda_evaluation.sagemaker_runtime')
    def test_invoke_endpoint_invalid_response(self, mock_sagemaker):
        """Test error handling when endpoint returns invalid JSON"""
        # Mock SageMaker to return invalid JSON
        mock_response = Mock()
        mock_response.read.return_value = b'invalid json'
        
        mock_sagemaker.invoke_endpoint.return_value = {
            'Body': mock_response
        }
        
        # Verify exception is raised
        with pytest.raises(json.JSONDecodeError):
            invoke_endpoint_for_predictions('test-endpoint', [1, 2], [10, 20])


class TestMetricCalculations:
    """Test metric calculation functions"""
    
    def test_calculate_rmse_perfect_predictions(self):
        """Test RMSE calculation with perfect predictions"""
        predictions = [4.0, 3.5, 5.0]
        actuals = [4.0, 3.5, 5.0]
        
        rmse = calculate_rmse(predictions, actuals)
        
        assert rmse == 0.0
    
    def test_calculate_mae_perfect_predictions(self):
        """Test MAE calculation with perfect predictions"""
        predictions = [4.0, 3.5, 5.0]
        actuals = [4.0, 3.5, 5.0]
        
        mae = calculate_mae(predictions, actuals)
        
        assert mae == 0.0
    
    def test_calculate_rmse_known_values(self):
        """Test RMSE calculation with known values"""
        predictions = [3.0, 4.0, 5.0]
        actuals = [3.0, 4.0, 4.0]
        
        # Expected: sqrt(mean([0, 0, 1])) = sqrt(1/3) ≈ 0.5774
        rmse = calculate_rmse(predictions, actuals)
        
        expected = np.sqrt(1.0 / 3.0)
        assert np.isclose(rmse, expected, rtol=1e-5)
    
    def test_calculate_mae_known_values(self):
        """Test MAE calculation with known values"""
        predictions = [3.0, 4.0, 5.0]
        actuals = [3.0, 4.0, 4.0]
        
        # Expected: mean([0, 0, 1]) = 1/3 ≈ 0.3333
        mae = calculate_mae(predictions, actuals)
        
        expected = 1.0 / 3.0
        assert np.isclose(mae, expected, rtol=1e-5)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
