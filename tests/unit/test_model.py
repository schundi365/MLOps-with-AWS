"""
Unit tests for the Collaborative Filtering Model

Tests cover:
- Model initialization
- Forward pass with known inputs
- Output shapes
- Gradient flow
"""

import pytest
import torch
import torch.nn as nn
from src.model import CollaborativeFilteringModel


class TestModelInitialization:
    """Test model initialization with various configurations"""
    
    def test_model_initialization_valid_params(self):
        """Test model initializes correctly with valid parameters"""
        num_users = 100
        num_movies = 50
        embedding_dim = 10
        
        model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim)
        
        assert model.num_users == num_users
        assert model.num_movies == num_movies
        assert model.embedding_dim == embedding_dim
        assert isinstance(model.user_embedding, nn.Embedding)
        assert isinstance(model.movie_embedding, nn.Embedding)
        assert isinstance(model.user_bias, nn.Embedding)
        assert isinstance(model.movie_bias, nn.Embedding)
    
    def test_model_embedding_dimensions(self):
        """Test that embeddings have correct dimensions"""
        num_users = 100
        num_movies = 50
        embedding_dim = 10
        
        model = CollaborativeFilteringModel(num_users, num_movies, embedding_dim)
        
        assert model.user_embedding.weight.shape == (num_users, embedding_dim)
        assert model.movie_embedding.weight.shape == (num_movies, embedding_dim)
        assert model.user_bias.weight.shape == (num_users, 1)
        assert model.movie_bias.weight.shape == (num_movies, 1)
    
    def test_model_initialization_invalid_num_users(self):
        """Test model raises error with invalid num_users"""
        with pytest.raises(ValueError, match="num_users must be positive"):
            CollaborativeFilteringModel(num_users=0, num_movies=50, embedding_dim=10)
        
        with pytest.raises(ValueError, match="num_users must be positive"):
            CollaborativeFilteringModel(num_users=-1, num_movies=50, embedding_dim=10)
    
    def test_model_initialization_invalid_num_movies(self):
        """Test model raises error with invalid num_movies"""
        with pytest.raises(ValueError, match="num_movies must be positive"):
            CollaborativeFilteringModel(num_users=100, num_movies=0, embedding_dim=10)
        
        with pytest.raises(ValueError, match="num_movies must be positive"):
            CollaborativeFilteringModel(num_users=100, num_movies=-1, embedding_dim=10)
    
    def test_model_initialization_invalid_embedding_dim(self):
        """Test model raises error with invalid embedding_dim"""
        with pytest.raises(ValueError, match="embedding_dim must be positive"):
            CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=0)
        
        with pytest.raises(ValueError, match="embedding_dim must be positive"):
            CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=-1)
    
    def test_model_weights_initialized(self):
        """Test that model weights are initialized (not all zeros)"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        # Embeddings should be initialized with small random values
        assert not torch.all(model.user_embedding.weight == 0)
        assert not torch.all(model.movie_embedding.weight == 0)
        
        # Biases should be initialized to zero
        assert torch.all(model.user_bias.weight == 0)
        assert torch.all(model.movie_bias.weight == 0)


class TestForwardPass:
    """Test forward pass with known inputs"""
    
    def test_forward_pass_single_sample(self):
        """Test forward pass with a single sample"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        user_ids = torch.tensor([0])
        movie_ids = torch.tensor([0])
        
        predictions = model(user_ids, movie_ids)
        
        assert predictions.shape == (1,)
        assert torch.all(torch.isfinite(predictions))
    
    def test_forward_pass_batch(self):
        """Test forward pass with a batch of samples"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        batch_size = 32
        user_ids = torch.randint(0, 100, (batch_size,))
        movie_ids = torch.randint(0, 50, (batch_size,))
        
        predictions = model(user_ids, movie_ids)
        
        assert predictions.shape == (batch_size,)
        assert torch.all(torch.isfinite(predictions))
    
    def test_forward_pass_known_values(self):
        """Test forward pass produces expected computation"""
        model = CollaborativeFilteringModel(num_users=10, num_movies=10, embedding_dim=5)
        
        # Set known weights for testing
        with torch.no_grad():
            model.user_embedding.weight.fill_(1.0)
            model.movie_embedding.weight.fill_(1.0)
            model.user_bias.weight.fill_(0.5)
            model.movie_bias.weight.fill_(0.3)
        
        user_ids = torch.tensor([0, 1])
        movie_ids = torch.tensor([0, 1])
        
        predictions = model(user_ids, movie_ids)
        
        # Expected: dot_product (1*1*5=5) + user_bias (0.5) + movie_bias (0.3) = 5.8
        expected = torch.tensor([5.8, 5.8])
        assert torch.allclose(predictions, expected, atol=1e-5)
    
    def test_forward_pass_different_users_movies(self):
        """Test that different user/movie combinations produce different predictions"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        user_ids_1 = torch.tensor([0, 1, 2])
        movie_ids_1 = torch.tensor([0, 1, 2])
        
        user_ids_2 = torch.tensor([3, 4, 5])
        movie_ids_2 = torch.tensor([3, 4, 5])
        
        predictions_1 = model(user_ids_1, movie_ids_1)
        predictions_2 = model(user_ids_2, movie_ids_2)
        
        # Different inputs should generally produce different outputs
        # (with very high probability given random initialization)
        assert not torch.allclose(predictions_1, predictions_2)


class TestOutputShapes:
    """Test output shapes for various input configurations"""
    
    def test_output_shape_single_prediction(self):
        """Test output shape for single prediction"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        user_ids = torch.tensor([5])
        movie_ids = torch.tensor([10])
        
        predictions = model(user_ids, movie_ids)
        
        assert predictions.shape == (1,)
        assert predictions.dim() == 1
    
    def test_output_shape_batch_predictions(self):
        """Test output shape for batch predictions"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        batch_sizes = [1, 8, 16, 32, 64, 128]
        
        for batch_size in batch_sizes:
            user_ids = torch.randint(0, 100, (batch_size,))
            movie_ids = torch.randint(0, 50, (batch_size,))
            
            predictions = model(user_ids, movie_ids)
            
            assert predictions.shape == (batch_size,)
            assert predictions.dim() == 1
    
    def test_output_shape_matches_input_length(self):
        """Test that output length matches input length"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        for length in [5, 10, 25, 50]:
            user_ids = torch.randint(0, 100, (length,))
            movie_ids = torch.randint(0, 50, (length,))
            
            predictions = model(user_ids, movie_ids)
            
            assert len(predictions) == length
            assert len(predictions) == len(user_ids)
            assert len(predictions) == len(movie_ids)


class TestGradientFlow:
    """Test gradient flow through the model"""
    
    def test_gradients_computed(self):
        """Test that gradients are computed for all parameters"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        user_ids = torch.tensor([0, 1, 2])
        movie_ids = torch.tensor([0, 1, 2])
        targets = torch.tensor([4.0, 3.5, 5.0])
        
        # Forward pass
        predictions = model(user_ids, movie_ids)
        
        # Compute loss
        loss = nn.MSELoss()(predictions, targets)
        
        # Backward pass
        loss.backward()
        
        # Check that gradients exist for all parameters
        assert model.user_embedding.weight.grad is not None
        assert model.movie_embedding.weight.grad is not None
        assert model.user_bias.weight.grad is not None
        assert model.movie_bias.weight.grad is not None
    
    def test_gradients_non_zero(self):
        """Test that gradients are non-zero after backward pass"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        user_ids = torch.tensor([0, 1, 2])
        movie_ids = torch.tensor([0, 1, 2])
        targets = torch.tensor([4.0, 3.5, 5.0])
        
        # Forward pass
        predictions = model(user_ids, movie_ids)
        
        # Compute loss
        loss = nn.MSELoss()(predictions, targets)
        
        # Backward pass
        loss.backward()
        
        # At least some gradients should be non-zero
        assert torch.any(model.user_embedding.weight.grad != 0)
        assert torch.any(model.movie_embedding.weight.grad != 0)
    
    def test_gradient_updates_parameters(self):
        """Test that gradient descent updates model parameters"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
        
        # Store initial weights
        initial_user_emb = model.user_embedding.weight.clone()
        initial_movie_emb = model.movie_embedding.weight.clone()
        
        user_ids = torch.tensor([0, 1, 2])
        movie_ids = torch.tensor([0, 1, 2])
        targets = torch.tensor([4.0, 3.5, 5.0])
        
        # Training step
        optimizer.zero_grad()
        predictions = model(user_ids, movie_ids)
        loss = nn.MSELoss()(predictions, targets)
        loss.backward()
        optimizer.step()
        
        # Check that weights have changed
        assert not torch.allclose(model.user_embedding.weight, initial_user_emb)
        assert not torch.allclose(model.movie_embedding.weight, initial_movie_emb)
    
    def test_multiple_backward_passes(self):
        """Test that multiple backward passes work correctly"""
        model = CollaborativeFilteringModel(num_users=100, num_movies=50, embedding_dim=10)
        
        for _ in range(5):
            user_ids = torch.randint(0, 100, (10,))
            movie_ids = torch.randint(0, 50, (10,))
            targets = torch.rand(10) * 5.0
            
            # Forward pass
            predictions = model(user_ids, movie_ids)
            
            # Compute loss
            loss = nn.MSELoss()(predictions, targets)
            
            # Backward pass
            model.zero_grad()
            loss.backward()
            
            # Check gradients exist
            assert model.user_embedding.weight.grad is not None
            assert model.movie_embedding.weight.grad is not None
