"""
SageMaker inference script for collaborative filtering model.

This script implements the required SageMaker inference functions:
- model_fn: Load model from artifacts
- input_fn: Parse JSON requests
- predict_fn: Generate predictions
- output_fn: Format JSON responses

Includes in-memory LRU cache for prediction results.

Validates: Requirements 5.1, 5.2, 5.3, 14.5
"""

import json
import logging
import os
from collections import OrderedDict
from pathlib import Path
import sys
from typing import Tuple

import torch
import torch.nn as nn

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent))
from model import CollaborativeFilteringModel


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LRUCache:
    """
    In-memory LRU (Least Recently Used) cache for prediction results.
    
    This cache stores predictions by (user_id, movie_id) key and evicts
    the least recently used entries when the cache reaches its size limit.
    
    Validates: Requirements 14.5
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize LRU cache.
        
        Args:
            max_size: Maximum number of entries to store in cache
        """
        self.max_size = max_size
        self.cache = OrderedDict()
        self.hits = 0
        self.misses = 0
        logger.info(f"Initialized LRU cache with max_size={max_size}")
    
    def get(self, key: Tuple[int, int]) -> float:
        """
        Get cached prediction for (user_id, movie_id) key.
        
        Args:
            key: Tuple of (user_id, movie_id)
        
        Returns:
            Cached prediction value, or None if not found
        """
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        else:
            self.misses += 1
            return None
    
    def put(self, key: Tuple[int, int], value: float) -> None:
        """
        Store prediction in cache.
        
        If cache is at max size, evicts the least recently used entry.
        
        Args:
            key: Tuple of (user_id, movie_id)
            value: Predicted rating value
        """
        if key in self.cache:
            # Update existing entry and move to end
            self.cache.move_to_end(key)
        else:
            # Add new entry
            if len(self.cache) >= self.max_size:
                # Evict least recently used (first item)
                evicted_key = next(iter(self.cache))
                del self.cache[evicted_key]
                logger.debug(f"Evicted cache entry for key {evicted_key}")
        
        self.cache[key] = value
    
    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with hits, misses, size, and hit rate
        """
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0.0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_rate': hit_rate
        }
    
    def clear(self) -> None:
        """Clear all cache entries and reset statistics."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        logger.info("Cache cleared")


# Global cache instance
_prediction_cache = None


def get_cache() -> LRUCache:
    """
    Get or create the global prediction cache instance.
    
    Returns:
        Global LRUCache instance
    """
    global _prediction_cache
    if _prediction_cache is None:
        # Default cache size of 10000 entries
        # Can be configured via environment variable
        cache_size = int(os.environ.get('PREDICTION_CACHE_SIZE', '10000'))
        _prediction_cache = LRUCache(max_size=cache_size)
    return _prediction_cache


def model_fn(model_dir: str) -> nn.Module:
    """
    Load model from artifacts directory.
    
    This function is called by SageMaker to load the model from the
    artifacts saved during training.
    
    Args:
        model_dir: Directory containing model artifacts (model.pth and metadata.json)
    
    Returns:
        Loaded PyTorch model ready for inference
    
    Raises:
        FileNotFoundError: If model files are not found
        ValueError: If metadata is invalid or missing required fields
    
    Validates: Requirements 5.1
    """
    logger.info(f"Loading model from {model_dir}")
    
    # Load metadata
    metadata_path = os.path.join(model_dir, 'metadata.json')
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found at {metadata_path}")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Validate metadata
    required_fields = ['num_users', 'num_movies', 'embedding_dim']
    missing_fields = [field for field in required_fields if field not in metadata]
    if missing_fields:
        raise ValueError(f"Metadata missing required fields: {missing_fields}")
    
    num_users = metadata['num_users']
    num_movies = metadata['num_movies']
    embedding_dim = metadata['embedding_dim']
    
    logger.info(f"Creating model with num_users={num_users}, num_movies={num_movies}, embedding_dim={embedding_dim}")
    
    # Create model architecture
    model = CollaborativeFilteringModel(
        num_users=num_users,
        num_movies=num_movies,
        embedding_dim=embedding_dim
    )
    
    # Load model weights
    model_path = os.path.join(model_dir, 'model.pth')
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found at {model_path}")
    
    # Load state dict
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    state_dict = torch.load(model_path, map_location=device)
    model.load_state_dict(state_dict)
    
    # Set model to evaluation mode
    model.eval()
    model = model.to(device)
    
    logger.info("Model loaded successfully")
    return model


def input_fn(request_body: str, content_type: str = 'application/json') -> dict:
    """
    Parse JSON input from inference request.
    
    This function is called by SageMaker to parse the incoming request body.
    
    Expected input format:
    {
        "user_ids": [123, 456, 789],
        "movie_ids": [1, 50, 100]
    }
    
    Args:
        request_body: Raw request body as string
        content_type: Content type of the request (default: 'application/json')
    
    Returns:
        Dictionary with parsed user_ids and movie_ids
    
    Raises:
        ValueError: If content type is not JSON or input format is invalid
    
    Validates: Requirements 5.2
    """
    logger.info(f"Parsing input with content_type={content_type}")
    
    # Validate content type
    if content_type != 'application/json':
        raise ValueError(f"Unsupported content type: {content_type}. Expected 'application/json'")
    
    # Parse JSON
    try:
        input_data = json.loads(request_body)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in request body: {e}")
    
    # Validate input structure
    if not isinstance(input_data, dict):
        raise ValueError("Input must be a JSON object")
    
    if 'user_ids' not in input_data:
        raise ValueError("Missing required field: 'user_ids'")
    
    if 'movie_ids' not in input_data:
        raise ValueError("Missing required field: 'movie_ids'")
    
    user_ids = input_data['user_ids']
    movie_ids = input_data['movie_ids']
    
    # Validate that both are lists
    if not isinstance(user_ids, list):
        raise ValueError("'user_ids' must be a list")
    
    if not isinstance(movie_ids, list):
        raise ValueError("'movie_ids' must be a list")
    
    # Validate that lists have the same length
    if len(user_ids) != len(movie_ids):
        raise ValueError(f"Length mismatch: user_ids has {len(user_ids)} elements, movie_ids has {len(movie_ids)} elements")
    
    # Validate that lists are not empty
    if len(user_ids) == 0:
        raise ValueError("Input lists cannot be empty")
    
    # Validate that all IDs are integers
    for i, user_id in enumerate(user_ids):
        if not isinstance(user_id, int):
            raise ValueError(f"user_ids[{i}] must be an integer, got {type(user_id).__name__}")
    
    for i, movie_id in enumerate(movie_ids):
        if not isinstance(movie_id, int):
            raise ValueError(f"movie_ids[{i}] must be an integer, got {type(movie_id).__name__}")
    
    # Validate that all IDs are non-negative
    for i, user_id in enumerate(user_ids):
        if user_id < 0:
            raise ValueError(f"user_ids[{i}] must be non-negative, got {user_id}")
    
    for i, movie_id in enumerate(movie_ids):
        if movie_id < 0:
            raise ValueError(f"movie_ids[{i}] must be non-negative, got {movie_id}")
    
    logger.info(f"Successfully parsed input with {len(user_ids)} predictions requested")
    
    return {
        'user_ids': user_ids,
        'movie_ids': movie_ids
    }


def predict_fn(input_data: dict, model: nn.Module) -> list:
    """
    Generate predictions using the loaded model.
    
    This function is called by SageMaker to generate predictions from the
    parsed input data. Uses LRU cache to avoid redundant predictions.
    
    Args:
        input_data: Dictionary with user_ids and movie_ids lists
        model: Loaded PyTorch model
    
    Returns:
        List of predicted ratings
    
    Raises:
        ValueError: If user_ids or movie_ids are out of valid range
    
    Validates: Requirements 5.1, 5.3, 14.5
    """
    logger.info("Generating predictions")
    
    user_ids = input_data['user_ids']
    movie_ids = input_data['movie_ids']
    
    # Validate ID ranges
    max_user_id = model.num_users - 1
    max_movie_id = model.num_movies - 1
    
    for i, user_id in enumerate(user_ids):
        if user_id > max_user_id:
            raise ValueError(f"user_ids[{i}]={user_id} exceeds maximum valid user ID {max_user_id}")
    
    for i, movie_id in enumerate(movie_ids):
        if movie_id > max_movie_id:
            raise ValueError(f"movie_ids[{i}]={movie_id} exceeds maximum valid movie ID {max_movie_id}")
    
    # Get cache instance
    cache = get_cache()
    
    # Check cache for each prediction
    predictions_list = []
    uncached_indices = []
    uncached_user_ids = []
    uncached_movie_ids = []
    
    for i, (user_id, movie_id) in enumerate(zip(user_ids, movie_ids)):
        cache_key = (user_id, movie_id)
        cached_prediction = cache.get(cache_key)
        
        if cached_prediction is not None:
            # Cache hit
            predictions_list.append(cached_prediction)
        else:
            # Cache miss - need to compute
            predictions_list.append(None)  # Placeholder
            uncached_indices.append(i)
            uncached_user_ids.append(user_id)
            uncached_movie_ids.append(movie_id)
    
    # Generate predictions for uncached entries
    if uncached_user_ids:
        logger.info(f"Computing {len(uncached_user_ids)} uncached predictions")
        
        # Convert to tensors
        device = next(model.parameters()).device
        user_ids_tensor = torch.LongTensor(uncached_user_ids).to(device)
        movie_ids_tensor = torch.LongTensor(uncached_movie_ids).to(device)
        
        # Generate predictions
        with torch.no_grad():
            uncached_predictions = model(user_ids_tensor, movie_ids_tensor)
        
        # Convert to list
        uncached_predictions_list = uncached_predictions.cpu().tolist()
        
        # Store in cache and update results
        for idx, pred in zip(uncached_indices, uncached_predictions_list):
            user_id = user_ids[idx]
            movie_id = movie_ids[idx]
            cache_key = (user_id, movie_id)
            
            # Store in cache
            cache.put(cache_key, pred)
            
            # Update results
            predictions_list[idx] = pred
    
    # Log cache statistics
    cache_stats = cache.get_stats()
    logger.info(f"Cache stats: {cache_stats}")
    logger.info(f"Generated {len(predictions_list)} predictions ({len(uncached_user_ids)} computed, {len(predictions_list) - len(uncached_user_ids)} cached)")
    
    return predictions_list


def output_fn(prediction: list, accept: str = 'application/json') -> str:
    """
    Format predictions as JSON response.
    
    This function is called by SageMaker to format the predictions into
    the response body.
    
    Output format:
    {
        "predictions": [4.2, 3.8, 4.5]
    }
    
    Args:
        prediction: List of predicted ratings
        accept: Accept header from request (default: 'application/json')
    
    Returns:
        JSON string with predictions
    
    Raises:
        ValueError: If accept type is not JSON
    
    Validates: Requirements 5.3
    """
    logger.info(f"Formatting output with accept={accept}")
    
    # Validate accept type
    if accept != 'application/json':
        raise ValueError(f"Unsupported accept type: {accept}. Expected 'application/json'")
    
    # Format output
    output = {
        'predictions': prediction
    }
    
    # Convert to JSON
    response_body = json.dumps(output)
    
    logger.info("Output formatted successfully")
    
    return response_body
