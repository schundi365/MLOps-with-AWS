"""
Property-based tests for model training components.

These tests validate universal correctness properties across many generated inputs.
"""

import io
import logging
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from hypothesis import given, settings, strategies as st, HealthCheck
import pytest

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / 'src'))


# Feature: aws-movielens-recommendation, Property 7: Training metrics are logged


@given(
    num_epochs=st.integers(min_value=1, max_value=3),
    num_samples=st.integers(min_value=50, max_value=100),
)
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
def test_training_metrics_are_logged(num_epochs, num_samples):
    """
    Property 7: Training metrics are logged
    
    For any training run, the training logs should contain both train RMSE and 
    validation RMSE values for each epoch.
    
    Validates: Requirements 3.6
    """
    # Create temporary directories for data and model
    with tempfile.TemporaryDirectory() as temp_dir:
        train_dir = os.path.join(temp_dir, 'train')
        val_dir = os.path.join(temp_dir, 'validation')
        model_dir = os.path.join(temp_dir, 'model')
        output_dir = os.path.join(temp_dir, 'output')
        
        os.makedirs(train_dir)
        os.makedirs(val_dir)
        os.makedirs(model_dir)
        os.makedirs(output_dir)
        
        # Generate synthetic training and validation data
        train_data = generate_training_data(num_samples, num_users=20, num_movies=30)
        val_data = generate_training_data(num_samples // 2, num_users=20, num_movies=30)
        
        # Save data to CSV files
        train_file = os.path.join(train_dir, 'train.csv')
        val_file = os.path.join(val_dir, 'validation.csv')
        train_data.to_csv(train_file, index=False)
        val_data.to_csv(val_file, index=False)
        
        # Set up logging capture
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        
        # Get the logger from train module
        from train import logger
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Create mock arguments for training
        class Args:
            def __init__(self):
                self.embedding_dim = 16
                self.learning_rate = 0.01
                self.batch_size = 32
                self.epochs = num_epochs
                self.num_factors = 50
                self.model_dir = model_dir
                self.train = train_dir
                self.validation = val_dir
                self.output_data_dir = output_dir
                self.num_gpus = 0  # Use CPU for testing
        
        args = Args()
        
        # Run training
        from train import train
        train(args)
        
        # Get the logged output
        log_output = log_stream.getvalue()
        
        # Property 1: Log output should contain training metrics for each epoch
        for epoch in range(1, num_epochs + 1):
            # Check that the epoch number appears in logs
            assert f"Epoch {epoch}/{num_epochs}" in log_output, \
                f"Log should contain 'Epoch {epoch}/{num_epochs}'"
        
        # Property 2: Log output should contain "Train RMSE" for each epoch
        train_rmse_count = log_output.count("Train RMSE:")
        assert train_rmse_count >= num_epochs, \
            f"Log should contain 'Train RMSE:' at least {num_epochs} times (once per epoch), found {train_rmse_count}"
        
        # Property 3: Log output should contain "Val RMSE" for each epoch
        val_rmse_count = log_output.count("Val RMSE:")
        assert val_rmse_count >= num_epochs, \
            f"Log should contain 'Val RMSE:' at least {num_epochs} times (once per epoch), found {val_rmse_count}"
        
        # Property 4: Each epoch should have both train and val RMSE logged together
        # Split log by lines and check that Train RMSE and Val RMSE appear in the same line
        log_lines = log_output.split('\n')
        epoch_metric_lines = [line for line in log_lines if 'Train RMSE:' in line and 'Val RMSE:' in line]
        assert len(epoch_metric_lines) >= num_epochs, \
            f"Should have at least {num_epochs} lines with both Train RMSE and Val RMSE, found {len(epoch_metric_lines)}"
        
        # Property 5: RMSE values should be numeric and positive
        import re
        train_rmse_pattern = r'Train RMSE: ([\d.]+)'
        val_rmse_pattern = r'Val RMSE: ([\d.]+)'
        
        train_rmse_values = re.findall(train_rmse_pattern, log_output)
        val_rmse_values = re.findall(val_rmse_pattern, log_output)
        
        assert len(train_rmse_values) >= num_epochs, \
            f"Should extract at least {num_epochs} train RMSE values, found {len(train_rmse_values)}"
        assert len(val_rmse_values) >= num_epochs, \
            f"Should extract at least {num_epochs} val RMSE values, found {len(val_rmse_values)}"
        
        # Check that all extracted RMSE values are valid positive numbers
        for rmse_str in train_rmse_values[:num_epochs]:
            rmse_value = float(rmse_str)
            assert rmse_value > 0, f"Train RMSE should be positive, got {rmse_value}"
            assert np.isfinite(rmse_value), f"Train RMSE should be finite, got {rmse_value}"
        
        for rmse_str in val_rmse_values[:num_epochs]:
            rmse_value = float(rmse_str)
            assert rmse_value > 0, f"Val RMSE should be positive, got {rmse_value}"
            assert np.isfinite(rmse_value), f"Val RMSE should be finite, got {rmse_value}"
        
        # Property 6: Training completion message should be logged
        assert "Training completed" in log_output or "Training script completed successfully" in log_output, \
            "Log should contain training completion message"
        
        # Property 7: Best validation RMSE should be logged
        assert "Best Val RMSE:" in log_output, \
            "Log should contain best validation RMSE"
        
        # Clean up handler
        logger.removeHandler(handler)


def generate_training_data(num_samples: int, num_users: int, num_movies: int) -> pd.DataFrame:
    """
    Generate synthetic training data with encoded IDs (consecutive integers from 0).
    
    Args:
        num_samples: Number of samples to generate
        num_users: Number of unique users
        num_movies: Number of unique movies
    
    Returns:
        DataFrame with userId, movieId, and rating columns
    """
    np.random.seed(None)  # Use different seed each time for property testing
    
    # Generate data with encoded IDs (0 to num_users-1, 0 to num_movies-1)
    data = pd.DataFrame({
        'userId': np.random.randint(0, num_users, size=num_samples),
        'movieId': np.random.randint(0, num_movies, size=num_samples),
        'rating': np.random.uniform(0.0, 1.0, size=num_samples)  # Normalized ratings
    })
    
    return data
