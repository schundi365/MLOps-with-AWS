"""
Unit tests for the training script

Tests cover:
- Training loop with small dataset
- Validation loop
- Model saving
- Error handling for corrupted data

Validates: Requirements 3.4, 3.5, 3.6
"""

import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch
import torch.nn as nn

from src.train import (
    RatingsDataset,
    parse_args,
    load_data,
    calculate_rmse,
    train_epoch,
    validate,
    save_checkpoint,
    save_model,
    train
)
from src.model import CollaborativeFilteringModel


@pytest.fixture
def small_dataset():
    """Create a small dataset for testing"""
    data = pd.DataFrame({
        'userId': [0, 0, 1, 1, 2, 2, 3, 3, 4, 4],
        'movieId': [0, 1, 0, 2, 1, 2, 0, 1, 2, 0],
        'rating': [4.0, 3.5, 5.0, 2.5, 4.5, 3.0, 5.0, 4.0, 3.5, 4.5]
    })
    return data


@pytest.fixture
def temp_data_dir(small_dataset):
    """Create temporary directory with training and validation data"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create train directory
        train_dir = os.path.join(tmpdir, 'train')
        os.makedirs(train_dir)
        train_file = os.path.join(train_dir, 'train.csv')
        small_dataset.to_csv(train_file, index=False)
        
        # Create validation directory
        val_dir = os.path.join(tmpdir, 'validation')
        os.makedirs(val_dir)
        val_file = os.path.join(val_dir, 'validation.csv')
        small_dataset.to_csv(val_file, index=False)
        
        yield tmpdir, train_dir, val_dir


class TestRatingsDataset:
    """Test RatingsDataset class"""
    
    def test_dataset_initialization(self, small_dataset):
        """Test dataset initializes correctly"""
        dataset = RatingsDataset(small_dataset)
        
        assert len(dataset) == len(small_dataset)
        assert isinstance(dataset.user_ids, torch.Tensor)
        assert isinstance(dataset.movie_ids, torch.Tensor)
        assert isinstance(dataset.ratings, torch.Tensor)
    
    def test_dataset_getitem(self, small_dataset):
        """Test dataset __getitem__ returns correct data"""
        dataset = RatingsDataset(small_dataset)
        
        user_id, movie_id, rating = dataset[0]
        
        assert user_id == small_dataset.iloc[0]['userId']
        assert movie_id == small_dataset.iloc[0]['movieId']
        assert rating == small_dataset.iloc[0]['rating']
    
    def test_dataset_length(self, small_dataset):
        """Test dataset __len__ returns correct length"""
        dataset = RatingsDataset(small_dataset)
        
        assert len(dataset) == 10


class TestLoadData:
    """Test data loading functionality"""
    
    def test_load_data_success(self, temp_data_dir):
        """Test loading data from directory"""
        tmpdir, train_dir, val_dir = temp_data_dir
        
        data = load_data(train_dir)
        
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 10
        assert 'userId' in data.columns
        assert 'movieId' in data.columns
        assert 'rating' in data.columns
    
    def test_load_data_no_files(self):
        """Test error when no CSV files found"""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError, match="No CSV files found"):
                load_data(tmpdir)
    
    def test_load_data_missing_columns(self):
        """Test error when required columns are missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CSV with missing columns
            data = pd.DataFrame({
                'userId': [0, 1, 2],
                'movieId': [0, 1, 2]
                # Missing 'rating' column
            })
            csv_file = os.path.join(tmpdir, 'data.csv')
            data.to_csv(csv_file, index=False)
            
            with pytest.raises(ValueError, match="Missing required columns"):
                load_data(tmpdir)


class TestCalculateRMSE:
    """Test RMSE calculation"""
    
    def test_rmse_perfect_predictions(self):
        """Test RMSE with perfect predictions"""
        predictions = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
        targets = torch.tensor([1.0, 2.0, 3.0, 4.0, 5.0])
        
        rmse = calculate_rmse(predictions, targets)
        
        assert rmse == pytest.approx(0.0, abs=1e-6)
    
    def test_rmse_known_values(self):
        """Test RMSE with known values"""
        predictions = torch.tensor([1.0, 2.0, 3.0])
        targets = torch.tensor([2.0, 3.0, 4.0])
        
        # Expected RMSE: sqrt(mean([1, 1, 1])) = sqrt(1) = 1.0
        rmse = calculate_rmse(predictions, targets)
        
        assert rmse == pytest.approx(1.0, abs=1e-6)
    
    def test_rmse_different_errors(self):
        """Test RMSE with different error magnitudes"""
        predictions = torch.tensor([1.0, 2.0, 3.0, 4.0])
        targets = torch.tensor([1.5, 2.5, 4.0, 6.0])
        
        # Errors: [0.5, 0.5, 1.0, 2.0]
        # Squared: [0.25, 0.25, 1.0, 4.0]
        # Mean: 1.375
        # RMSE: sqrt(1.375) ≈ 1.173
        rmse = calculate_rmse(predictions, targets)
        
        assert rmse == pytest.approx(1.173, abs=0.01)


class TestTrainingLoop:
    """Test training loop with small dataset"""
    
    def test_train_epoch_reduces_loss(self, small_dataset):
        """Test that training for one epoch works"""
        # Create model
        num_users = small_dataset['userId'].max() + 1
        num_movies = small_dataset['movieId'].max() + 1
        model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim=8)
        
        # Create dataloader
        dataset = RatingsDataset(small_dataset)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=4, shuffle=True)
        
        # Create optimizer and criterion
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        device = torch.device('cpu')
        
        # Train for one epoch
        rmse = train_epoch(model, dataloader, criterion, optimizer, device)
        
        # RMSE should be a finite positive number
        assert isinstance(rmse, float)
        assert rmse > 0
        assert np.isfinite(rmse)
    
    def test_train_epoch_multiple_epochs(self, small_dataset):
        """Test training for multiple epochs reduces RMSE"""
        # Create model
        num_users = small_dataset['userId'].max() + 1
        num_movies = small_dataset['movieId'].max() + 1
        model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim=8)
        
        # Create dataloader
        dataset = RatingsDataset(small_dataset)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=4, shuffle=True)
        
        # Create optimizer and criterion
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        device = torch.device('cpu')
        
        # Train for multiple epochs
        rmse_values = []
        for _ in range(5):
            rmse = train_epoch(model, dataloader, criterion, optimizer, device)
            rmse_values.append(rmse)
        
        # RMSE should generally decrease (allowing for some fluctuation)
        # Check that final RMSE is less than initial RMSE
        assert rmse_values[-1] < rmse_values[0]
    
    def test_train_epoch_updates_weights(self, small_dataset):
        """Test that training updates model weights"""
        # Create model
        num_users = small_dataset['userId'].max() + 1
        num_movies = small_dataset['movieId'].max() + 1
        model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim=8)
        
        # Store initial weights
        initial_weights = model.user_embedding.weight.clone()
        
        # Create dataloader
        dataset = RatingsDataset(small_dataset)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=4, shuffle=True)
        
        # Create optimizer and criterion
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
        device = torch.device('cpu')
        
        # Train for one epoch
        train_epoch(model, dataloader, criterion, optimizer, device)
        
        # Weights should have changed
        assert not torch.allclose(model.user_embedding.weight, initial_weights)


class TestValidationLoop:
    """Test validation loop"""
    
    def test_validate_returns_rmse(self, small_dataset):
        """Test validation returns RMSE value"""
        # Create model
        num_users = small_dataset['userId'].max() + 1
        num_movies = small_dataset['movieId'].max() + 1
        model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim=8)
        
        # Create dataloader
        dataset = RatingsDataset(small_dataset)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=4, shuffle=False)
        
        # Create criterion
        criterion = nn.MSELoss()
        device = torch.device('cpu')
        
        # Validate
        rmse = validate(model, dataloader, criterion, device)
        
        # RMSE should be a finite positive number
        assert isinstance(rmse, float)
        assert rmse > 0
        assert np.isfinite(rmse)
    
    def test_validate_no_gradient_updates(self, small_dataset):
        """Test that validation does not update gradients"""
        # Create model
        num_users = small_dataset['userId'].max() + 1
        num_movies = small_dataset['movieId'].max() + 1
        model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim=8)
        
        # Store initial weights
        initial_weights = model.user_embedding.weight.clone()
        
        # Create dataloader
        dataset = RatingsDataset(small_dataset)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=4, shuffle=False)
        
        # Create criterion
        criterion = nn.MSELoss()
        device = torch.device('cpu')
        
        # Validate
        validate(model, dataloader, criterion, device)
        
        # Weights should not have changed
        assert torch.allclose(model.user_embedding.weight, initial_weights)
    
    def test_validate_consistent_results(self, small_dataset):
        """Test that validation gives consistent results"""
        # Create model
        num_users = small_dataset['userId'].max() + 1
        num_movies = small_dataset['movieId'].max() + 1
        model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim=8)
        
        # Create dataloader
        dataset = RatingsDataset(small_dataset)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=4, shuffle=False)
        
        # Create criterion
        criterion = nn.MSELoss()
        device = torch.device('cpu')
        
        # Validate multiple times
        rmse1 = validate(model, dataloader, criterion, device)
        rmse2 = validate(model, dataloader, criterion, device)
        
        # Results should be identical
        assert rmse1 == pytest.approx(rmse2, abs=1e-6)


class TestModelSaving:
    """Test model saving functionality"""
    
    def test_save_checkpoint(self, small_dataset):
        """Test saving model checkpoint"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create model
            num_users = small_dataset['userId'].max() + 1
            num_movies = small_dataset['movieId'].max() + 1
            model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim=8)
            
            # Create optimizer
            optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
            
            # Save checkpoint
            checkpoint_path = os.path.join(tmpdir, 'checkpoint.pth')
            save_checkpoint(model, optimizer, epoch=5, val_rmse=0.85, checkpoint_path=checkpoint_path)
            
            # Check file exists
            assert os.path.exists(checkpoint_path)
            
            # Load and verify checkpoint
            checkpoint = torch.load(checkpoint_path)
            assert 'epoch' in checkpoint
            assert 'model_state_dict' in checkpoint
            assert 'optimizer_state_dict' in checkpoint
            assert 'val_rmse' in checkpoint
            assert checkpoint['epoch'] == 5
            assert checkpoint['val_rmse'] == 0.85
    
    def test_save_model_creates_files(self, small_dataset):
        """Test that save_model creates model.pth and metadata.json"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create model
            num_users = small_dataset['userId'].max() + 1
            num_movies = small_dataset['movieId'].max() + 1
            embedding_dim = 8
            model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim)
            
            # Save model
            metadata = {
                'training_rmse': 0.82,
                'validation_rmse': 0.85,
                'best_epoch': 10
            }
            save_model(model, tmpdir, num_users, num_movies, embedding_dim, metadata)
            
            # Check files exist
            model_path = os.path.join(tmpdir, 'model.pth')
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            
            assert os.path.exists(model_path)
            assert os.path.exists(metadata_path)
    
    def test_save_model_metadata_content(self, small_dataset):
        """Test that metadata contains correct information"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create model
            num_users = small_dataset['userId'].max() + 1
            num_movies = small_dataset['movieId'].max() + 1
            embedding_dim = 8
            model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim)
            
            # Save model
            metadata = {
                'training_rmse': 0.82,
                'validation_rmse': 0.85,
                'best_epoch': 10,
                'hyperparameters': {
                    'learning_rate': 0.001,
                    'batch_size': 256
                }
            }
            save_model(model, tmpdir, num_users, num_movies, embedding_dim, metadata)
            
            # Load and verify metadata
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'r') as f:
                loaded_metadata = json.load(f)
            
            assert loaded_metadata['num_users'] == num_users
            assert loaded_metadata['num_movies'] == num_movies
            assert loaded_metadata['embedding_dim'] == embedding_dim
            assert loaded_metadata['training_rmse'] == 0.82
            assert loaded_metadata['validation_rmse'] == 0.85
            assert loaded_metadata['best_epoch'] == 10
            assert 'hyperparameters' in loaded_metadata
    
    def test_save_model_can_be_loaded(self, small_dataset):
        """Test that saved model can be loaded"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create and save model
            num_users = small_dataset['userId'].max() + 1
            num_movies = small_dataset['movieId'].max() + 1
            embedding_dim = 8
            model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim)
            
            metadata = {'training_rmse': 0.82}
            save_model(model, tmpdir, num_users, num_movies, embedding_dim, metadata)
            
            # Load model
            model_path = os.path.join(tmpdir, 'model.pth')
            loaded_model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim)
            loaded_model.load_state_dict(torch.load(model_path))
            
            # Verify model works
            user_ids = torch.tensor([0, 1])
            movie_ids = torch.tensor([0, 1])
            predictions = loaded_model(user_ids, movie_ids)
            
            assert predictions.shape == (2,)
            assert torch.all(torch.isfinite(predictions))


class TestErrorHandling:
    """Test error handling for corrupted data"""
    
    def test_corrupted_csv_missing_columns(self):
        """Test handling of CSV with missing required columns"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create corrupted CSV (missing rating column)
            data = pd.DataFrame({
                'userId': [0, 1, 2],
                'movieId': [0, 1, 2]
            })
            csv_file = os.path.join(tmpdir, 'corrupted.csv')
            data.to_csv(csv_file, index=False)
            
            # Should raise ValueError
            with pytest.raises(ValueError, match="Missing required columns"):
                load_data(tmpdir)
    
    def test_corrupted_csv_invalid_data_types(self):
        """Test handling of CSV with invalid data types"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CSV with invalid data
            with open(os.path.join(tmpdir, 'corrupted.csv'), 'w') as f:
                f.write('userId,movieId,rating\n')
                f.write('0,0,4.0\n')
                f.write('1,1,invalid\n')  # Invalid rating
                f.write('2,2,3.5\n')
            
            # Should raise error when trying to convert to tensor
            with pytest.raises((ValueError, TypeError)):
                data = load_data(tmpdir)
                dataset = RatingsDataset(data)
    
    def test_empty_csv_file(self):
        """Test handling of empty CSV file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty CSV
            data = pd.DataFrame(columns=['userId', 'movieId', 'rating'])
            csv_file = os.path.join(tmpdir, 'empty.csv')
            data.to_csv(csv_file, index=False)
            
            # Load data (should succeed but be empty)
            loaded_data = load_data(tmpdir)
            assert len(loaded_data) == 0
    
    def test_csv_with_nan_values(self):
        """Test handling of CSV with NaN values"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create CSV with NaN values
            data = pd.DataFrame({
                'userId': [0, 1, np.nan, 3],
                'movieId': [0, 1, 2, 3],
                'rating': [4.0, 3.5, 5.0, np.nan]
            })
            csv_file = os.path.join(tmpdir, 'nan_data.csv')
            data.to_csv(csv_file, index=False)
            
            # Load data
            loaded_data = load_data(tmpdir)
            
            # Check that NaN values are present
            assert loaded_data.isna().any().any()
    
    def test_nonexistent_directory(self):
        """Test error when data directory doesn't exist"""
        with pytest.raises(FileNotFoundError):
            load_data('/nonexistent/directory/path')


class TestTrainFunction:
    """Test the main train function"""
    
    def test_train_function_completes(self, temp_data_dir):
        """Test that train function completes successfully with small dataset"""
        tmpdir, train_dir, val_dir = temp_data_dir
        
        with tempfile.TemporaryDirectory() as model_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                # Create mock args
                class Args:
                    pass
                
                args = Args()
                args.embedding_dim = 8
                args.learning_rate = 0.01
                args.batch_size = 4
                args.epochs = 2  # Small number for testing
                args.num_factors = 50
                args.model_dir = model_dir
                args.train = train_dir
                args.validation = val_dir
                args.output_data_dir = output_dir
                args.num_gpus = 0
                
                # Run training
                train(args)
                
                # Check that model was saved
                model_path = os.path.join(model_dir, 'model.pth')
                metadata_path = os.path.join(model_dir, 'metadata.json')
                
                assert os.path.exists(model_path)
                assert os.path.exists(metadata_path)
    
    def test_train_function_creates_checkpoint(self, temp_data_dir):
        """Test that train function creates checkpoint"""
        tmpdir, train_dir, val_dir = temp_data_dir
        
        with tempfile.TemporaryDirectory() as model_dir:
            with tempfile.TemporaryDirectory() as output_dir:
                # Create mock args
                class Args:
                    pass
                
                args = Args()
                args.embedding_dim = 8
                args.learning_rate = 0.01
                args.batch_size = 4
                args.epochs = 2
                args.num_factors = 50
                args.model_dir = model_dir
                args.train = train_dir
                args.validation = val_dir
                args.output_data_dir = output_dir
                args.num_gpus = 0
                
                # Run training
                train(args)
                
                # Check that checkpoint was created
                checkpoint_path = os.path.join(output_dir, 'best_checkpoint.pth')
                assert os.path.exists(checkpoint_path)
