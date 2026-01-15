"""
Data preprocessing module for MovieLens recommendation system.

This module handles data loading, cleaning, transformation, and splitting
for the collaborative filtering model.
"""

import pandas as pd
import numpy as np
from typing import Tuple


def handle_missing_values(data: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing values in the dataset by removing rows with missing required fields.
    
    Required fields: userId, movieId, rating
    
    Args:
        data: DataFrame with potential missing values
    
    Returns:
        DataFrame with no missing values in required fields
    
    Validates: Requirements 2.1
    """
    # Drop rows where any of the required fields are missing
    required_fields = ['userId', 'movieId', 'rating']
    
    # Create a copy to avoid modifying the original
    cleaned_data = data.copy()
    
    # Drop rows with missing values in required fields
    cleaned_data = cleaned_data.dropna(subset=required_fields)
    
    return cleaned_data


def encode_ids(data: pd.DataFrame) -> Tuple[pd.DataFrame, dict, dict]:
    """
    Encode user and movie IDs as consecutive integers starting from 0.
    
    This function creates mappings from original IDs to encoded IDs (0, 1, 2, ...).
    The encoded IDs are consecutive with no gaps, which is required for embedding layers.
    
    Args:
        data: DataFrame with userId and movieId columns
    
    Returns:
        Tuple of (encoded_data, user_id_map, movie_id_map) where:
        - encoded_data: DataFrame with encoded userId and movieId
        - user_id_map: Dictionary mapping original userId to encoded userId
        - movie_id_map: Dictionary mapping original movieId to encoded movieId
    
    Validates: Requirements 2.2
    """
    # Create a copy to avoid modifying the original
    encoded_data = data.copy()
    
    # Get unique user and movie IDs, sorted for consistency
    unique_users = sorted(data['userId'].unique())
    unique_movies = sorted(data['movieId'].unique())
    
    # Create mappings from original IDs to consecutive integers
    user_id_map = {original_id: encoded_id for encoded_id, original_id in enumerate(unique_users)}
    movie_id_map = {original_id: encoded_id for encoded_id, original_id in enumerate(unique_movies)}
    
    # Apply the mappings to the data
    encoded_data['userId'] = encoded_data['userId'].map(user_id_map)
    encoded_data['movieId'] = encoded_data['movieId'].map(movie_id_map)
    
    return encoded_data, user_id_map, movie_id_map


def create_user_item_matrix(data: pd.DataFrame) -> np.ndarray:
    """
    Create a user-item interaction matrix from ratings data.
    
    The matrix has dimensions (num_users, num_movies) where each cell contains
    the rating given by a user to a movie. Unrated items are represented as 0.
    
    Note: This function expects the data to have encoded IDs (consecutive integers
    starting from 0). Call encode_ids() first if needed.
    
    Args:
        data: DataFrame with userId, movieId, and rating columns (with encoded IDs)
    
    Returns:
        2D numpy array of shape (num_users, num_movies) containing ratings
    
    Validates: Requirements 2.3
    """
    # Get the number of unique users and movies
    num_users = data['userId'].max() + 1
    num_movies = data['movieId'].max() + 1
    
    # Initialize matrix with zeros
    matrix = np.zeros((num_users, num_movies))
    
    # Fill in the ratings
    for _, row in data.iterrows():
        user_id = int(row['userId'])
        movie_id = int(row['movieId'])
        rating = row['rating']
        matrix[user_id, movie_id] = rating
    
    return matrix


def split_data(data: pd.DataFrame, train_ratio: float = 0.8, 
               val_ratio: float = 0.1, test_ratio: float = 0.1,
               random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split data into training, validation, and test sets.
    
    The default split is 80% train, 10% validation, 10% test.
    The data is shuffled before splitting to ensure randomness.
    
    Uses rounding to nearest integer to minimize rounding errors and ensure
    split ratios are as close as possible to the target ratios.
    
    Args:
        data: DataFrame to split
        train_ratio: Proportion of data for training (default: 0.8)
        val_ratio: Proportion of data for validation (default: 0.1)
        test_ratio: Proportion of data for testing (default: 0.1)
        random_state: Random seed for reproducibility (default: 42)
    
    Returns:
        Tuple of (train_data, val_data, test_data)
    
    Validates: Requirements 2.4
    """
    # Validate that ratios sum to 1.0
    total_ratio = train_ratio + val_ratio + test_ratio
    if not np.isclose(total_ratio, 1.0, rtol=1e-5):
        raise ValueError(f"Ratios must sum to 1.0, got {total_ratio}")
    
    # Shuffle the data
    shuffled_data = data.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    
    # Calculate split indices using rounding to minimize errors
    n = len(shuffled_data)
    
    # Round train size to nearest integer
    train_size = round(n * train_ratio)
    
    # Round validation size to nearest integer
    val_size = round(n * val_ratio)
    
    # Test gets the remainder to ensure all data is used
    test_size = n - train_size - val_size
    
    # Adjust if test_size is negative (can happen with rounding)
    if test_size < 0:
        # Reduce train_size to accommodate
        train_size += test_size
        test_size = 0
    
    # Calculate split indices
    train_end = train_size
    val_end = train_end + val_size
    
    # Split the data
    train_data = shuffled_data.iloc[:train_end].copy()
    val_data = shuffled_data.iloc[train_end:val_end].copy()
    test_data = shuffled_data.iloc[val_end:].copy()
    
    return train_data, val_data, test_data


def normalize_ratings(data: pd.DataFrame, min_rating: float = 0.5, 
                      max_rating: float = 5.0) -> pd.DataFrame:
    """
    Normalize rating values to [0, 1] range.
    
    This function applies min-max normalization to scale ratings from their
    original range (typically 0.5 to 5.0 for MovieLens) to [0, 1].
    
    Formula: normalized = (rating - min_rating) / (max_rating - min_rating)
    
    Args:
        data: DataFrame with a 'rating' column
        min_rating: Minimum rating value in the original scale (default: 0.5)
        max_rating: Maximum rating value in the original scale (default: 5.0)
    
    Returns:
        DataFrame with normalized ratings in [0, 1] range
    
    Validates: Requirements 2.5
    """
    # Create a copy to avoid modifying the original
    normalized_data = data.copy()
    
    # Apply min-max normalization
    normalized_data['rating'] = (normalized_data['rating'] - min_rating) / (max_rating - min_rating)
    
    # Clip values to ensure they're strictly in [0, 1] range
    # (in case of any ratings outside the expected range)
    normalized_data['rating'] = normalized_data['rating'].clip(0.0, 1.0)
    
    return normalized_data
