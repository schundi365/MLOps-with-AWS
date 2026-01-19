"""
Collaborative Filtering Model for MovieLens Recommendation System

This module implements a neural collaborative filtering model using matrix factorization
to predict user ratings for movies.
"""

import torch
import torch.nn as nn


class CollaborativeFilteringModel(nn.Module):
    """
    Collaborative filtering model using matrix factorization.
    
    The model learns embeddings for users and movies, along with bias terms,
    to predict ratings through dot product computation.
    
    Args:
        num_users: Total number of unique users
        num_movies: Total number of unique movies
        embedding_dim: Dimensionality of user and movie embeddings
    """
    
    def __init__(self, num_users: int, num_movies: int, embedding_dim: int):
        super(CollaborativeFilteringModel, self).__init__()
        
        # Validate inputs
        if num_users <= 0:
            raise ValueError(f"num_users must be positive, got {num_users}")
        if num_movies <= 0:
            raise ValueError(f"num_movies must be positive, got {num_movies}")
        if embedding_dim <= 0:
            raise ValueError(f"embedding_dim must be positive, got {embedding_dim}")
        
        self.num_users = num_users
        self.num_movies = num_movies
        self.embedding_dim = embedding_dim
        
        # User and movie embeddings
        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.movie_embedding = nn.Embedding(num_movies, embedding_dim)
        
        # Bias terms
        self.user_bias = nn.Embedding(num_users, 1)
        self.movie_bias = nn.Embedding(num_movies, 1)
        
        # Initialize embeddings with small random values
        self._init_weights()
    
    def _init_weights(self):
        """Initialize embedding weights with small random values"""
        nn.init.normal_(self.user_embedding.weight, mean=0.0, std=0.01)
        nn.init.normal_(self.movie_embedding.weight, mean=0.0, std=0.01)
        nn.init.zeros_(self.user_bias.weight)
        nn.init.zeros_(self.movie_bias.weight)
    
    def forward(self, user_ids: torch.Tensor, movie_ids: torch.Tensor) -> torch.Tensor:
        """
        Forward pass to compute predicted ratings.
        
        Args:
            user_ids: Tensor of user IDs, shape (batch_size,)
            movie_ids: Tensor of movie IDs, shape (batch_size,)
        
        Returns:
            Predicted ratings, shape (batch_size,)
        """
        # Get embeddings
        user_emb = self.user_embedding(user_ids)  # (batch_size, embedding_dim)
        movie_emb = self.movie_embedding(movie_ids)  # (batch_size, embedding_dim)
        
        # Compute dot product
        dot_product = (user_emb * movie_emb).sum(dim=1)  # (batch_size,)
        
        # Add bias terms
        user_b = self.user_bias(user_ids).squeeze()  # (batch_size,)
        movie_b = self.movie_bias(movie_ids).squeeze()  # (batch_size,)
        
        # Final prediction
        prediction = dot_product + user_b + movie_b
        
        return prediction
