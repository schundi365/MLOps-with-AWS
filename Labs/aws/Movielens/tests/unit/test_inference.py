"""
Unit tests for the SageMaker inference script

Tests cover:
- Model loading from artifacts
- Input parsing with valid JSON
- Input parsing with invalid JSON
- Prediction generation
- Output formatting

Validates: Requirements 5.1, 5.2, 5.3
"""

import json
import os
import tempfile
from pathlib import Path

import pytest
import torch
import torch.nn as nn

from src.inference import model_fn, input_fn, predict_fn, output_fn
from src.model import CollaborativeFilteringModel


class TestModelLoading:
    """Test model_fn for loading model from artifacts"""
    
    def test_model_loading_success(self):
        """Test model loads successfully with valid artifacts"""
        # Create temporary directory for model artifacts
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            metadata = {
                'num_users': 100,
                'num_movies': 50,
                'embedding_dim': 10,
                'training_rmse': 0.82,
                'validation_rmse': 0.85
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Create and save model
            model = CollaborativeFilteringModel(
                num_users=100,
                num_movies=50,
                embedding_dim=10
            )
            
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(model.state_dict(), model_path)
            
            # Load model using model_fn
            loaded_model = model_fn(tmpdir)
            
            # Verify model is loaded correctly
            assert isinstance(loaded_model, nn.Module)
            assert hasattr(loaded_model, 'num_users')
            assert hasattr(loaded_model, 'num_movies')
            assert hasattr(loaded_model, 'embedding_dim')
            assert loaded_model.num_users == 100
            assert loaded_model.num_movies == 50
            assert loaded_model.embedding_dim == 10
            
            # Verify model is in eval mode
            assert not loaded_model.training
    
    def test_model_loading_missing_metadata(self):
        """Test model loading fails when metadata is missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create model but no metadata
            model = CollaborativeFilteringModel(
                num_users=100,
                num_movies=50,
                embedding_dim=10
            )
            
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(model.state_dict(), model_path)
            
            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError, match="Metadata file not found"):
                model_fn(tmpdir)
    
    def test_model_loading_missing_model_file(self):
        """Test model loading fails when model.pth is missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata but no model file
            metadata = {
                'num_users': 100,
                'num_movies': 50,
                'embedding_dim': 10
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Should raise FileNotFoundError
            with pytest.raises(FileNotFoundError, match="Model file not found"):
                model_fn(tmpdir)
    
    def test_model_loading_invalid_metadata(self):
        """Test model loading fails with invalid metadata"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata missing required fields
            metadata = {
                'num_users': 100,
                # Missing num_movies and embedding_dim
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Should raise ValueError
            with pytest.raises(ValueError, match="Metadata missing required fields"):
                model_fn(tmpdir)
    
    def test_model_loading_preserves_weights(self):
        """Test that loaded model has the same weights as saved model"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            metadata = {
                'num_users': 100,
                'num_movies': 50,
                'embedding_dim': 10
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Create model with specific weights
            original_model = CollaborativeFilteringModel(
                num_users=100,
                num_movies=50,
                embedding_dim=10
            )
            
            # Set some specific weights for testing
            with torch.no_grad():
                original_model.user_embedding.weight[0, :] = torch.ones(10) * 0.5
                original_model.movie_embedding.weight[0, :] = torch.ones(10) * 0.3
            
            # Save model
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(original_model.state_dict(), model_path)
            
            # Load model
            loaded_model = model_fn(tmpdir)
            
            # Verify weights are preserved
            assert torch.allclose(
                loaded_model.user_embedding.weight[0, :],
                original_model.user_embedding.weight[0, :]
            )
            assert torch.allclose(
                loaded_model.movie_embedding.weight[0, :],
                original_model.movie_embedding.weight[0, :]
            )


class TestInputParsing:
    """Test input_fn for parsing JSON requests"""
    
    def test_input_parsing_valid_json(self):
        """Test input parsing with valid JSON"""
        request_body = json.dumps({
            'user_ids': [1, 2, 3],
            'movie_ids': [10, 20, 30]
        })
        
        result = input_fn(request_body, 'application/json')
        
        assert result == {
            'user_ids': [1, 2, 3],
            'movie_ids': [10, 20, 30]
        }
    
    def test_input_parsing_single_prediction(self):
        """Test input parsing with single prediction request"""
        request_body = json.dumps({
            'user_ids': [5],
            'movie_ids': [15]
        })
        
        result = input_fn(request_body, 'application/json')
        
        assert result == {
            'user_ids': [5],
            'movie_ids': [15]
        }
    
    def test_input_parsing_large_batch(self):
        """Test input parsing with large batch"""
        user_ids = list(range(100))
        movie_ids = list(range(100, 200))
        
        request_body = json.dumps({
            'user_ids': user_ids,
            'movie_ids': movie_ids
        })
        
        result = input_fn(request_body, 'application/json')
        
        assert result['user_ids'] == user_ids
        assert result['movie_ids'] == movie_ids
    
    def test_input_parsing_invalid_json(self):
        """Test input parsing with invalid JSON"""
        request_body = "not valid json {{"
        
        with pytest.raises(ValueError, match="Invalid JSON"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_wrong_content_type(self):
        """Test input parsing rejects non-JSON content type"""
        request_body = json.dumps({
            'user_ids': [1, 2, 3],
            'movie_ids': [10, 20, 30]
        })
        
        with pytest.raises(ValueError, match="Unsupported content type"):
            input_fn(request_body, 'text/plain')
    
    def test_input_parsing_missing_user_ids(self):
        """Test input parsing fails when user_ids is missing"""
        request_body = json.dumps({
            'movie_ids': [10, 20, 30]
        })
        
        with pytest.raises(ValueError, match="Missing required field: 'user_ids'"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_missing_movie_ids(self):
        """Test input parsing fails when movie_ids is missing"""
        request_body = json.dumps({
            'user_ids': [1, 2, 3]
        })
        
        with pytest.raises(ValueError, match="Missing required field: 'movie_ids'"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_not_dict(self):
        """Test input parsing fails when input is not a dictionary"""
        request_body = json.dumps([1, 2, 3])
        
        with pytest.raises(ValueError, match="Input must be a JSON object"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_user_ids_not_list(self):
        """Test input parsing fails when user_ids is not a list"""
        request_body = json.dumps({
            'user_ids': 123,
            'movie_ids': [10, 20, 30]
        })
        
        with pytest.raises(ValueError, match="'user_ids' must be a list"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_movie_ids_not_list(self):
        """Test input parsing fails when movie_ids is not a list"""
        request_body = json.dumps({
            'user_ids': [1, 2, 3],
            'movie_ids': "not a list"
        })
        
        with pytest.raises(ValueError, match="'movie_ids' must be a list"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_length_mismatch(self):
        """Test input parsing fails when list lengths don't match"""
        request_body = json.dumps({
            'user_ids': [1, 2, 3],
            'movie_ids': [10, 20]
        })
        
        with pytest.raises(ValueError, match="Length mismatch"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_empty_lists(self):
        """Test input parsing fails with empty lists"""
        request_body = json.dumps({
            'user_ids': [],
            'movie_ids': []
        })
        
        with pytest.raises(ValueError, match="Input lists cannot be empty"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_non_integer_user_id(self):
        """Test input parsing fails with non-integer user_id"""
        request_body = json.dumps({
            'user_ids': [1, "two", 3],
            'movie_ids': [10, 20, 30]
        })
        
        with pytest.raises(ValueError, match="user_ids\\[1\\] must be an integer"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_non_integer_movie_id(self):
        """Test input parsing fails with non-integer movie_id"""
        request_body = json.dumps({
            'user_ids': [1, 2, 3],
            'movie_ids': [10, 20.5, 30]
        })
        
        with pytest.raises(ValueError, match="movie_ids\\[1\\] must be an integer"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_negative_user_id(self):
        """Test input parsing fails with negative user_id"""
        request_body = json.dumps({
            'user_ids': [1, -2, 3],
            'movie_ids': [10, 20, 30]
        })
        
        with pytest.raises(ValueError, match="user_ids\\[1\\] must be non-negative"):
            input_fn(request_body, 'application/json')
    
    def test_input_parsing_negative_movie_id(self):
        """Test input parsing fails with negative movie_id"""
        request_body = json.dumps({
            'user_ids': [1, 2, 3],
            'movie_ids': [10, -20, 30]
        })
        
        with pytest.raises(ValueError, match="movie_ids\\[1\\] must be non-negative"):
            input_fn(request_body, 'application/json')


class TestPredictionGeneration:
    """Test predict_fn for generating predictions"""
    
    def test_prediction_generation_single(self):
        """Test prediction generation for single input"""
        model = CollaborativeFilteringModel(
            num_users=100,
            num_movies=50,
            embedding_dim=10
        )
        model.eval()
        
        input_data = {
            'user_ids': [5],
            'movie_ids': [10]
        }
        
        predictions = predict_fn(input_data, model)
        
        assert isinstance(predictions, list)
        assert len(predictions) == 1
        assert isinstance(predictions[0], float)
    
    def test_prediction_generation_batch(self):
        """Test prediction generation for batch input"""
        model = CollaborativeFilteringModel(
            num_users=100,
            num_movies=50,
            embedding_dim=10
        )
        model.eval()
        
        input_data = {
            'user_ids': [1, 2, 3, 4, 5],
            'movie_ids': [10, 20, 30, 40, 45]
        }
        
        predictions = predict_fn(input_data, model)
        
        assert isinstance(predictions, list)
        assert len(predictions) == 5
        assert all(isinstance(p, float) for p in predictions)
    
    def test_prediction_generation_deterministic(self):
        """Test that predictions are deterministic for same input"""
        model = CollaborativeFilteringModel(
            num_users=100,
            num_movies=50,
            embedding_dim=10
        )
        model.eval()
        
        input_data = {
            'user_ids': [5, 10, 15],
            'movie_ids': [10, 20, 30]
        }
        
        predictions_1 = predict_fn(input_data, model)
        predictions_2 = predict_fn(input_data, model)
        
        assert predictions_1 == predictions_2
    
    def test_prediction_generation_user_id_out_of_range(self):
        """Test prediction fails when user_id exceeds valid range"""
        model = CollaborativeFilteringModel(
            num_users=100,
            num_movies=50,
            embedding_dim=10
        )
        model.eval()
        
        input_data = {
            'user_ids': [5, 150],  # 150 is out of range (max is 99)
            'movie_ids': [10, 20]
        }
        
        with pytest.raises(ValueError, match="user_ids\\[1\\]=150 exceeds maximum valid user ID"):
            predict_fn(input_data, model)
    
    def test_prediction_generation_movie_id_out_of_range(self):
        """Test prediction fails when movie_id exceeds valid range"""
        model = CollaborativeFilteringModel(
            num_users=100,
            num_movies=50,
            embedding_dim=10
        )
        model.eval()
        
        input_data = {
            'user_ids': [5, 10],
            'movie_ids': [10, 60]  # 60 is out of range (max is 49)
        }
        
        with pytest.raises(ValueError, match="movie_ids\\[1\\]=60 exceeds maximum valid movie ID"):
            predict_fn(input_data, model)
    
    def test_prediction_generation_valid_boundary_ids(self):
        """Test prediction works with boundary valid IDs"""
        model = CollaborativeFilteringModel(
            num_users=100,
            num_movies=50,
            embedding_dim=10
        )
        model.eval()
        
        input_data = {
            'user_ids': [0, 99],  # Min and max valid user IDs
            'movie_ids': [0, 49]  # Min and max valid movie IDs
        }
        
        predictions = predict_fn(input_data, model)
        
        assert len(predictions) == 2
        assert all(isinstance(p, float) for p in predictions)
    
    def test_prediction_generation_uses_model_device(self):
        """Test that predictions use the same device as model"""
        model = CollaborativeFilteringModel(
            num_users=100,
            num_movies=50,
            embedding_dim=10
        )
        model.eval()
        
        # Model is on CPU by default
        input_data = {
            'user_ids': [5, 10],
            'movie_ids': [10, 20]
        }
        
        # Should not raise any device mismatch errors
        predictions = predict_fn(input_data, model)
        
        assert len(predictions) == 2


class TestOutputFormatting:
    """Test output_fn for formatting JSON responses"""
    
    def test_output_formatting_single_prediction(self):
        """Test output formatting for single prediction"""
        predictions = [4.2]
        
        output = output_fn(predictions, 'application/json')
        
        assert isinstance(output, str)
        
        # Parse JSON to verify structure
        parsed = json.loads(output)
        assert 'predictions' in parsed
        assert parsed['predictions'] == [4.2]
    
    def test_output_formatting_multiple_predictions(self):
        """Test output formatting for multiple predictions"""
        predictions = [4.2, 3.8, 4.5, 2.1]
        
        output = output_fn(predictions, 'application/json')
        
        assert isinstance(output, str)
        
        # Parse JSON to verify structure
        parsed = json.loads(output)
        assert 'predictions' in parsed
        assert parsed['predictions'] == predictions
    
    def test_output_formatting_empty_predictions(self):
        """Test output formatting with empty predictions list"""
        predictions = []
        
        output = output_fn(predictions, 'application/json')
        
        assert isinstance(output, str)
        
        # Parse JSON to verify structure
        parsed = json.loads(output)
        assert 'predictions' in parsed
        assert parsed['predictions'] == []
    
    def test_output_formatting_wrong_accept_type(self):
        """Test output formatting rejects non-JSON accept type"""
        predictions = [4.2, 3.8]
        
        with pytest.raises(ValueError, match="Unsupported accept type"):
            output_fn(predictions, 'text/plain')
    
    def test_output_formatting_valid_json(self):
        """Test that output is valid JSON"""
        predictions = [4.2, 3.8, 4.5]
        
        output = output_fn(predictions, 'application/json')
        
        # Should not raise JSONDecodeError
        parsed = json.loads(output)
        assert isinstance(parsed, dict)
    
    def test_output_formatting_preserves_precision(self):
        """Test that output preserves floating point precision"""
        predictions = [4.123456789, 3.987654321]
        
        output = output_fn(predictions, 'application/json')
        
        parsed = json.loads(output)
        
        # Check that precision is preserved (within floating point limits)
        assert abs(parsed['predictions'][0] - 4.123456789) < 1e-9
        assert abs(parsed['predictions'][1] - 3.987654321) < 1e-9


class TestEndToEndInference:
    """Test end-to-end inference pipeline"""
    
    def test_end_to_end_inference_pipeline(self):
        """Test complete inference pipeline from input to output"""
        # Create and save model
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            metadata = {
                'num_users': 100,
                'num_movies': 50,
                'embedding_dim': 10
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Create and save model
            model = CollaborativeFilteringModel(
                num_users=100,
                num_movies=50,
                embedding_dim=10
            )
            
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(model.state_dict(), model_path)
            
            # Load model
            loaded_model = model_fn(tmpdir)
            
            # Parse input
            request_body = json.dumps({
                'user_ids': [5, 10, 15],
                'movie_ids': [10, 20, 30]
            })
            
            input_data = input_fn(request_body, 'application/json')
            
            # Generate predictions
            predictions = predict_fn(input_data, loaded_model)
            
            # Format output
            output = output_fn(predictions, 'application/json')
            
            # Verify output
            parsed_output = json.loads(output)
            assert 'predictions' in parsed_output
            assert len(parsed_output['predictions']) == 3
            assert all(isinstance(p, float) for p in parsed_output['predictions'])
    
    def test_end_to_end_with_error_handling(self):
        """Test that errors are properly propagated through pipeline"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            metadata = {
                'num_users': 100,
                'num_movies': 50,
                'embedding_dim': 10
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Create and save model
            model = CollaborativeFilteringModel(
                num_users=100,
                num_movies=50,
                embedding_dim=10
            )
            
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(model.state_dict(), model_path)
            
            # Load model
            loaded_model = model_fn(tmpdir)
            
            # Try with invalid input (user_id out of range)
            request_body = json.dumps({
                'user_ids': [5, 150],  # 150 is out of range
                'movie_ids': [10, 20]
            })
            
            input_data = input_fn(request_body, 'application/json')
            
            # Should raise error during prediction
            with pytest.raises(ValueError, match="exceeds maximum valid user ID"):
                predict_fn(input_data, loaded_model)


class TestCaching:
    """Test caching functionality in inference"""
    
    def test_cache_hit_returns_same_result(self):
        """Test that cached predictions return identical results"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            metadata = {
                'num_users': 100,
                'num_movies': 50,
                'embedding_dim': 10
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Create and save model
            model = CollaborativeFilteringModel(
                num_users=100,
                num_movies=50,
                embedding_dim=10
            )
            
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(model.state_dict(), model_path)
            
            # Load model
            loaded_model = model_fn(tmpdir)
            
            # Clear cache to start fresh
            from src.inference import get_cache
            cache = get_cache()
            cache.clear()
            
            # First prediction (cache miss)
            input_data1 = {
                'user_ids': [5, 10],
                'movie_ids': [10, 20]
            }
            predictions1 = predict_fn(input_data1, loaded_model)
            
            # Second prediction with same inputs (cache hit)
            input_data2 = {
                'user_ids': [5, 10],
                'movie_ids': [10, 20]
            }
            predictions2 = predict_fn(input_data2, loaded_model)
            
            # Verify predictions are identical
            assert predictions1 == predictions2
            assert len(predictions1) == 2
            
            # Verify cache was used
            stats = cache.get_stats()
            assert stats['hits'] >= 2  # Both predictions should be cache hits on second call
    
    def test_cache_partial_hit(self):
        """Test that cache works correctly with partial hits"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            metadata = {
                'num_users': 100,
                'num_movies': 50,
                'embedding_dim': 10
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Create and save model
            model = CollaborativeFilteringModel(
                num_users=100,
                num_movies=50,
                embedding_dim=10
            )
            
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(model.state_dict(), model_path)
            
            # Load model
            loaded_model = model_fn(tmpdir)
            
            # Clear cache
            from src.inference import get_cache
            cache = get_cache()
            cache.clear()
            
            # First prediction
            input_data1 = {
                'user_ids': [5, 10],
                'movie_ids': [10, 20]
            }
            predictions1 = predict_fn(input_data1, loaded_model)
            
            # Second prediction with one cached and one new
            input_data2 = {
                'user_ids': [5, 15],  # 5 is cached, 15 is new
                'movie_ids': [10, 25]  # 10 is cached, 25 is new
            }
            predictions2 = predict_fn(input_data2, loaded_model)
            
            # Verify first prediction matches
            assert predictions2[0] == predictions1[0]
            
            # Verify cache stats show partial hit
            stats = cache.get_stats()
            assert stats['hits'] >= 1
            assert stats['misses'] >= 1
    
    def test_cache_eviction(self):
        """Test that cache evicts least recently used entries"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            metadata = {
                'num_users': 1000,
                'num_movies': 500,
                'embedding_dim': 10
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Create and save model
            model = CollaborativeFilteringModel(
                num_users=1000,
                num_movies=500,
                embedding_dim=10
            )
            
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(model.state_dict(), model_path)
            
            # Load model
            loaded_model = model_fn(tmpdir)
            
            # Create small cache for testing eviction
            from src.inference import get_cache, _prediction_cache
            import src.inference as inference_module
            
            # Replace global cache with small one
            small_cache = inference_module.LRUCache(max_size=5)
            inference_module._prediction_cache = small_cache
            
            # Fill cache beyond capacity
            for i in range(10):
                input_data = {
                    'user_ids': [i],
                    'movie_ids': [i]
                }
                predict_fn(input_data, loaded_model)
            
            # Verify cache size is at max
            assert len(small_cache.cache) == 5
            
            # Verify oldest entries were evicted
            # The last 5 entries should be in cache
            for i in range(5, 10):
                assert (i, i) in small_cache.cache
            
            # First 5 entries should be evicted
            for i in range(5):
                assert (i, i) not in small_cache.cache
    
    def test_cache_statistics(self):
        """Test that cache statistics are tracked correctly"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metadata
            metadata = {
                'num_users': 100,
                'num_movies': 50,
                'embedding_dim': 10
            }
            
            metadata_path = os.path.join(tmpdir, 'metadata.json')
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Create and save model
            model = CollaborativeFilteringModel(
                num_users=100,
                num_movies=50,
                embedding_dim=10
            )
            
            model_path = os.path.join(tmpdir, 'model.pth')
            torch.save(model.state_dict(), model_path)
            
            # Load model
            loaded_model = model_fn(tmpdir)
            
            # Clear cache
            from src.inference import get_cache
            cache = get_cache()
            cache.clear()
            
            # Make predictions
            input_data1 = {
                'user_ids': [5],
                'movie_ids': [10]
            }
            predict_fn(input_data1, loaded_model)  # Miss
            
            input_data2 = {
                'user_ids': [5],
                'movie_ids': [10]
            }
            predict_fn(input_data2, loaded_model)  # Hit
            
            # Check statistics
            stats = cache.get_stats()
            assert stats['hits'] >= 1
            assert stats['misses'] >= 1
            assert stats['size'] >= 1
            assert 0.0 <= stats['hit_rate'] <= 1.0
