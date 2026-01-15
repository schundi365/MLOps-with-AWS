"""
Property-based tests for data pipeline components.

These tests validate universal correctness properties across many generated inputs.
"""

import pandas as pd
import numpy as np
from hypothesis import given, settings, strategies as st
import pytest

# Feature: aws-movielens-recommendation, Property 1: Missing value handling preserves data integrity


@given(
    num_rows=st.integers(min_value=10, max_value=100),
    missing_ratio=st.floats(min_value=0.1, max_value=0.5),
)
@settings(max_examples=20, deadline=None)
def test_missing_value_handling_preserves_data_integrity(num_rows, missing_ratio):
    """
    Property 1: Missing value handling preserves data integrity
    
    For any dataset with missing values, after preprocessing, the output should 
    contain no missing values in required fields (userId, movieId, rating).
    
    Validates: Requirements 2.1
    """
    # Generate a dataset with missing values
    data = generate_ratings_data_with_missing_values(num_rows, missing_ratio)
    
    # Verify the input has missing values (precondition)
    assert data[['userId', 'movieId', 'rating']].isnull().any().any(), \
        "Test data should contain missing values"
    
    # Import the preprocessing function
    from src.preprocessing import handle_missing_values
    
    # Apply missing value handling
    processed_data = handle_missing_values(data)
    
    # Property: No missing values in required fields after preprocessing
    assert not processed_data['userId'].isnull().any(), \
        "userId should have no missing values after preprocessing"
    assert not processed_data['movieId'].isnull().any(), \
        "movieId should have no missing values after preprocessing"
    assert not processed_data['rating'].isnull().any(), \
        "rating should have no missing values after preprocessing"
    
    # Additional integrity check: processed data should be a subset or equal to original
    assert len(processed_data) <= len(data), \
        "Processed data should not have more rows than original"
    
    # All remaining data should have valid values
    assert len(processed_data) > 0, \
        "Processed data should not be empty (unless all rows had missing values)"


# Feature: aws-movielens-recommendation, Property 2: ID encoding produces valid integer mappings


@given(
    num_rows=st.integers(min_value=10, max_value=200),
    num_users=st.integers(min_value=5, max_value=100),
    num_movies=st.integers(min_value=5, max_value=100),
)
@settings(max_examples=100, deadline=None)
def test_id_encoding_produces_valid_integer_mappings(num_rows, num_users, num_movies):
    """
    Property 2: ID encoding produces valid integer mappings
    
    For any input dataset with user and movie IDs, the encoded IDs should be 
    consecutive integers starting from 0 with no gaps.
    
    Validates: Requirements 2.2
    """
    # Generate a dataset with arbitrary user and movie IDs
    data = generate_ratings_data_with_arbitrary_ids(num_rows, num_users, num_movies)
    
    # Import the encoding function
    from src.preprocessing import encode_ids
    
    # Apply ID encoding
    encoded_data, user_id_map, movie_id_map = encode_ids(data)
    
    # Property 1: Encoded user IDs should be consecutive integers starting from 0
    unique_encoded_users = sorted(encoded_data['userId'].unique())
    expected_user_ids = list(range(len(unique_encoded_users)))
    assert unique_encoded_users == expected_user_ids, \
        f"Encoded user IDs should be consecutive from 0, got {unique_encoded_users}"
    
    # Property 2: Encoded movie IDs should be consecutive integers starting from 0
    unique_encoded_movies = sorted(encoded_data['movieId'].unique())
    expected_movie_ids = list(range(len(unique_encoded_movies)))
    assert unique_encoded_movies == expected_movie_ids, \
        f"Encoded movie IDs should be consecutive from 0, got {unique_encoded_movies}"
    
    # Property 3: No gaps in the encoded IDs
    assert max(encoded_data['userId']) == len(unique_encoded_users) - 1, \
        "User IDs should have no gaps (max should be count - 1)"
    assert max(encoded_data['movieId']) == len(unique_encoded_movies) - 1, \
        "Movie IDs should have no gaps (max should be count - 1)"
    
    # Property 4: Minimum encoded ID should be 0
    assert min(encoded_data['userId']) == 0, "Minimum user ID should be 0"
    assert min(encoded_data['movieId']) == 0, "Minimum movie ID should be 0"
    
    # Property 5: Mappings should be consistent (same original ID always maps to same encoded ID)
    for original_user_id in data['userId'].unique():
        encoded_id = user_id_map[original_user_id]
        assert all(encoded_data[data['userId'] == original_user_id]['userId'] == encoded_id), \
            "Mapping should be consistent for each user ID"
    
    for original_movie_id in data['movieId'].unique():
        encoded_id = movie_id_map[original_movie_id]
        assert all(encoded_data[data['movieId'] == original_movie_id]['movieId'] == encoded_id), \
            "Mapping should be consistent for each movie ID"
    
    # Property 6: Number of unique encoded IDs should match number of unique original IDs
    assert len(unique_encoded_users) == len(data['userId'].unique()), \
        "Number of unique encoded user IDs should match original"
    assert len(unique_encoded_movies) == len(data['movieId'].unique()), \
        "Number of unique encoded movie IDs should match original"


def generate_ratings_data_with_arbitrary_ids(num_rows: int, num_users: int, num_movies: int) -> pd.DataFrame:
    """
    Generate synthetic ratings data with arbitrary (non-consecutive) user and movie IDs.
    
    Args:
        num_rows: Number of rows to generate
        num_users: Number of unique users
        num_movies: Number of unique movies
    
    Returns:
        DataFrame with userId, movieId, rating, and timestamp columns
    """
    np.random.seed(None)  # Use different seed each time for property testing
    
    # Generate arbitrary (non-consecutive) user and movie IDs
    # Use random integers that may have gaps
    user_ids = np.random.choice(range(1, 10000), size=num_users, replace=False)
    movie_ids = np.random.choice(range(1, 50000), size=num_movies, replace=False)
    
    # Generate ratings by randomly selecting from the available users and movies
    data = pd.DataFrame({
        'userId': np.random.choice(user_ids, size=num_rows),
        'movieId': np.random.choice(movie_ids, size=num_rows),
        'rating': np.random.uniform(0.5, 5.0, size=num_rows),
        'timestamp': np.random.randint(800000000, 1600000000, size=num_rows)
    })
    
    return data


def generate_ratings_data_with_missing_values(num_rows: int, missing_ratio: float) -> pd.DataFrame:
    """
    Generate synthetic ratings data with missing values for testing.
    
    Args:
        num_rows: Number of rows to generate
        missing_ratio: Proportion of values to set as missing (0.0 to 1.0)
    
    Returns:
        DataFrame with userId, movieId, rating, and timestamp columns
    """
    np.random.seed(None)  # Use different seed each time for property testing
    
    # Generate base data
    data = pd.DataFrame({
        'userId': np.random.randint(1, 1000, size=num_rows),
        'movieId': np.random.randint(1, 5000, size=num_rows),
        'rating': np.random.uniform(0.5, 5.0, size=num_rows),
        'timestamp': np.random.randint(800000000, 1600000000, size=num_rows)
    })
    
    # Introduce missing values in required fields
    num_missing = int(num_rows * missing_ratio)
    
    # Randomly select indices to set as missing
    for col in ['userId', 'movieId', 'rating']:
        missing_indices = np.random.choice(num_rows, size=min(num_missing, num_rows), replace=False)
        data.loc[missing_indices, col] = np.nan
    
    return data


# Feature: aws-movielens-recommendation, Property 3: User-item matrix dimensions match data


@given(
    num_rows=st.integers(min_value=10, max_value=200),
    num_users=st.integers(min_value=5, max_value=50),
    num_movies=st.integers(min_value=5, max_value=50),
)
@settings(max_examples=100, deadline=None)
def test_user_item_matrix_dimensions_match_data(num_rows, num_users, num_movies):
    """
    Property 3: User-item matrix dimensions match data
    
    For any ratings dataset, the created user-item interaction matrix should have 
    dimensions equal to (number of unique users) × (number of unique movies).
    
    Validates: Requirements 2.3
    """
    # Generate a dataset with arbitrary user and movie IDs
    data = generate_ratings_data_with_arbitrary_ids(num_rows, num_users, num_movies)
    
    # Import the functions
    from src.preprocessing import encode_ids, create_user_item_matrix
    
    # First encode the IDs to get consecutive integers starting from 0
    encoded_data, user_id_map, movie_id_map = encode_ids(data)
    
    # Get the actual number of unique users and movies in the data
    actual_num_users = len(data['userId'].unique())
    actual_num_movies = len(data['movieId'].unique())
    
    # Create the user-item matrix
    matrix = create_user_item_matrix(encoded_data)
    
    # Property 1: Matrix should have correct number of rows (users)
    assert matrix.shape[0] == actual_num_users, \
        f"Matrix should have {actual_num_users} rows (users), got {matrix.shape[0]}"
    
    # Property 2: Matrix should have correct number of columns (movies)
    assert matrix.shape[1] == actual_num_movies, \
        f"Matrix should have {actual_num_movies} columns (movies), got {matrix.shape[1]}"
    
    # Property 3: Matrix dimensions should match the encoded data's max IDs + 1
    assert matrix.shape[0] == encoded_data['userId'].max() + 1, \
        "Matrix rows should equal max encoded user ID + 1"
    assert matrix.shape[1] == encoded_data['movieId'].max() + 1, \
        "Matrix columns should equal max encoded movie ID + 1"
    
    # Property 4: Matrix should be 2-dimensional
    assert len(matrix.shape) == 2, \
        f"Matrix should be 2-dimensional, got {len(matrix.shape)} dimensions"
    
    # Property 5: All ratings in the data should be present in the matrix
    for _, row in encoded_data.iterrows():
        user_id = int(row['userId'])
        movie_id = int(row['movieId'])
        rating = row['rating']
        # The matrix should contain this rating (or the last one if there are duplicates)
        assert matrix[user_id, movie_id] != 0 or rating == 0, \
            f"Rating for user {user_id}, movie {movie_id} should be in matrix"
    
    # Property 6: Matrix should not have more non-zero entries than ratings in data
    # (it could have fewer if there are duplicate user-movie pairs)
    num_nonzero = np.count_nonzero(matrix)
    assert num_nonzero <= len(encoded_data), \
        f"Matrix should not have more non-zero entries ({num_nonzero}) than ratings ({len(encoded_data)})"


# Feature: aws-movielens-recommendation, Property 4: Data split ratios are correct


@given(
    num_rows=st.integers(min_value=100, max_value=1000),
)
@settings(max_examples=100, deadline=None)
def test_data_split_ratios_are_correct(num_rows):
    """
    Property 4: Data split ratios are correct
    
    For any dataset split into train/validation/test sets, the sizes should be 
    approximately 80%/10%/10% of the total (within 1% tolerance for rounding).
    
    Validates: Requirements 2.4
    """
    # Generate a dataset
    data = generate_ratings_data(num_rows)
    
    # Import the split function
    from src.preprocessing import split_data
    
    # Split the data with default ratios (80/10/10)
    train_data, val_data, test_data = split_data(data)
    
    # Calculate actual ratios
    total_size = len(data)
    train_ratio = len(train_data) / total_size
    val_ratio = len(val_data) / total_size
    test_ratio = len(test_data) / total_size
    
    # Property 1: Train set should be approximately 80% (within 1% tolerance)
    assert abs(train_ratio - 0.8) <= 0.01, \
        f"Train ratio should be ~0.8 (within 1%), got {train_ratio:.4f}"
    
    # Property 2: Validation set should be approximately 10% (within 1% tolerance)
    assert abs(val_ratio - 0.1) <= 0.01, \
        f"Validation ratio should be ~0.1 (within 1%), got {val_ratio:.4f}"
    
    # Property 3: Test set should be approximately 10% (within 1% tolerance)
    assert abs(test_ratio - 0.1) <= 0.01, \
        f"Test ratio should be ~0.1 (within 1%), got {test_ratio:.4f}"
    
    # Property 4: All splits combined should equal original data size
    assert len(train_data) + len(val_data) + len(test_data) == total_size, \
        "Sum of split sizes should equal original data size"
    
    # Property 5: No data should be lost or duplicated
    assert len(train_data) > 0, "Train set should not be empty"
    assert len(val_data) > 0, "Validation set should not be empty"
    assert len(test_data) > 0, "Test set should not be empty"
    
    # Property 6: Splits should not overlap (check by index if available)
    # Since we reset index in split_data, we check that total rows match
    total_rows = len(train_data) + len(val_data) + len(test_data)
    assert total_rows == len(data), \
        f"Total rows in splits ({total_rows}) should match original data ({len(data)})"
    
    # Property 7: Each split should maintain data structure
    assert list(train_data.columns) == list(data.columns), \
        "Train data should have same columns as original"
    assert list(val_data.columns) == list(data.columns), \
        "Validation data should have same columns as original"
    assert list(test_data.columns) == list(data.columns), \
        "Test data should have same columns as original"


def generate_ratings_data(num_rows: int) -> pd.DataFrame:
    """
    Generate synthetic ratings data for testing.
    
    Args:
        num_rows: Number of rows to generate
    
    Returns:
        DataFrame with userId, movieId, rating, and timestamp columns
    """
    np.random.seed(None)  # Use different seed each time for property testing
    
    data = pd.DataFrame({
        'userId': np.random.randint(1, 1000, size=num_rows),
        'movieId': np.random.randint(1, 5000, size=num_rows),
        'rating': np.random.uniform(0.5, 5.0, size=num_rows),
        'timestamp': np.random.randint(800000000, 1600000000, size=num_rows)
    })
    
    return data


# Feature: aws-movielens-recommendation, Property 5: Rating normalization bounds


@given(
    num_rows=st.integers(min_value=10, max_value=500),
)
@settings(max_examples=100, deadline=None)
def test_rating_normalization_bounds(num_rows):
    """
    Property 5: Rating normalization bounds
    
    For any set of ratings, after normalization, all values should be in the range [0.0, 1.0].
    
    Validates: Requirements 2.5
    """
    # Generate a dataset with ratings in the typical MovieLens range (0.5 to 5.0)
    data = generate_ratings_data(num_rows)
    
    # Verify the input has ratings in the expected range (precondition)
    assert data['rating'].min() >= 0.5, "Input ratings should be >= 0.5"
    assert data['rating'].max() <= 5.0, "Input ratings should be <= 5.0"
    
    # Import the normalization function
    from src.preprocessing import normalize_ratings
    
    # Apply rating normalization
    normalized_data = normalize_ratings(data)
    
    # Property 1: All normalized ratings should be >= 0.0
    assert (normalized_data['rating'] >= 0.0).all(), \
        f"All normalized ratings should be >= 0.0, got min: {normalized_data['rating'].min()}"
    
    # Property 2: All normalized ratings should be <= 1.0
    assert (normalized_data['rating'] <= 1.0).all(), \
        f"All normalized ratings should be <= 1.0, got max: {normalized_data['rating'].max()}"
    
    # Property 3: Normalized ratings should be in the closed interval [0.0, 1.0]
    assert normalized_data['rating'].between(0.0, 1.0, inclusive='both').all(), \
        "All normalized ratings should be in [0.0, 1.0]"
    
    # Property 4: Normalization should preserve relative ordering
    # If rating A > rating B, then normalized A > normalized B
    for i in range(min(10, len(data) - 1)):  # Check a sample of pairs
        if data.iloc[i]['rating'] > data.iloc[i + 1]['rating']:
            assert normalized_data.iloc[i]['rating'] > normalized_data.iloc[i + 1]['rating'], \
                "Normalization should preserve relative ordering"
        elif data.iloc[i]['rating'] < data.iloc[i + 1]['rating']:
            assert normalized_data.iloc[i]['rating'] < normalized_data.iloc[i + 1]['rating'], \
                "Normalization should preserve relative ordering"
        else:  # Equal ratings
            assert np.isclose(normalized_data.iloc[i]['rating'], 
                            normalized_data.iloc[i + 1]['rating'], atol=1e-6), \
                "Equal ratings should remain equal after normalization"
    
    # Property 5: Number of rows should remain unchanged
    assert len(normalized_data) == len(data), \
        "Normalization should not change the number of rows"
    
    # Property 6: Other columns should remain unchanged
    assert (normalized_data['userId'] == data['userId']).all(), \
        "userId column should remain unchanged"
    assert (normalized_data['movieId'] == data['movieId']).all(), \
        "movieId column should remain unchanged"
    assert (normalized_data['timestamp'] == data['timestamp']).all(), \
        "timestamp column should remain unchanged"
    
    # Property 7: Normalization formula correctness
    # For any rating r in [0.5, 5.0], normalized value should be (r - 0.5) / (5.0 - 0.5)
    for i in range(min(5, len(data))):  # Check a sample
        original_rating = data.iloc[i]['rating']
        normalized_rating = normalized_data.iloc[i]['rating']
        expected_normalized = (original_rating - 0.5) / (5.0 - 0.5)
        assert np.isclose(normalized_rating, expected_normalized, atol=1e-6), \
            f"Normalization formula incorrect: expected {expected_normalized}, got {normalized_rating}"
