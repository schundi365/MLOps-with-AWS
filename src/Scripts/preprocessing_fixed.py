"""
MovieLens Data Preprocessing for SageMaker Processing Job

This script runs as a SageMaker processing job to:
1. Load raw MovieLens data from /opt/ml/processing/input/data/
2. Clean and transform the data
3. Split into train/validation/test sets
4. Save processed data to /opt/ml/processing/output/
"""
import pandas as pd
import numpy as np
import os
import sys


def load_movielens_data(input_path):
    """Load MovieLens dataset (supports both 100K u.data and Latest Small ratings.csv)"""
    print("[INFO] Loading MovieLens data...")
    
    # The S3 raw-data folder is mounted, so files are in a subdirectory
    # Try multiple possible locations for both formats
    possible_paths = [
        # MovieLens Latest Small format (CSV)
        (os.path.join(input_path, 'data', 'ratings.csv'), 'csv'),
        (os.path.join(input_path, 'data', 'raw-data', 'ratings.csv'), 'csv'),
        (os.path.join(input_path, 'ratings.csv'), 'csv'),
        # MovieLens 100K format (tab-separated)
        (os.path.join(input_path, 'data', 'u.data'), 'tsv'),
        (os.path.join(input_path, 'data', 'raw-data', 'u.data'), 'tsv'),
        (os.path.join(input_path, 'u.data'), 'tsv'),
    ]
    
    ratings_file = None
    file_format = None
    for path, fmt in possible_paths:
        if os.path.exists(path):
            ratings_file = path
            file_format = fmt
            print(f"[INFO] Found ratings file at: {ratings_file} (format: {fmt})")
            break
    
    if not ratings_file:
        print(f"[ERROR] Ratings file not found in any expected location")
        print(f"[INFO] Searched paths:")
        for path, fmt in possible_paths:
            print(f"  - {path} ({fmt})")
        print(f"[INFO] Contents of {input_path}:")
        for root, dirs, files in os.walk(input_path):
            level = root.replace(input_path, '').count(os.sep)
            indent = ' ' * 2 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                print(f"{subindent}{file}")
        sys.exit(1)
    
    # Load ratings based on format
    if file_format == 'csv':
        # MovieLens Latest Small format: CSV with header
        # Columns: userId,movieId,rating,timestamp
        ratings = pd.read_csv(ratings_file)
        print(f"[INFO] Loaded CSV format with columns: {list(ratings.columns)}")
    else:
        # MovieLens 100K format: tab-separated, no header
        ratings = pd.read_csv(
            ratings_file,
            sep='\t',
            names=['userId', 'movieId', 'rating', 'timestamp'],
            engine='python'
        )
        print(f"[INFO] Loaded TSV format (MovieLens 100K)")
    
    print(f"[INFO] Loaded {len(ratings)} ratings")
    print(f"[INFO] Users: {ratings['userId'].nunique()}, Movies: {ratings['movieId'].nunique()}")
    
    return ratings


def clean_data(data):
    """Remove missing values"""
    print("[INFO] Cleaning data...")
    
    # Drop rows with missing values in required fields
    required_fields = ['userId', 'movieId', 'rating']
    cleaned = data.dropna(subset=required_fields)
    
    print(f"[INFO] Removed {len(data) - len(cleaned)} rows with missing values")
    
    return cleaned


def encode_ids(data):
    """Encode user and movie IDs as consecutive integers"""
    print("[INFO] Encoding IDs...")
    
    encoded_data = data.copy()
    
    # Create mappings
    unique_users = sorted(data['userId'].unique())
    unique_movies = sorted(data['movieId'].unique())
    
    user_id_map = {original: encoded for encoded, original in enumerate(unique_users)}
    movie_id_map = {original: encoded for encoded, original in enumerate(unique_movies)}
    
    # Apply mappings
    encoded_data['userId'] = encoded_data['userId'].map(user_id_map)
    encoded_data['movieId'] = encoded_data['movieId'].map(movie_id_map)
    
    print(f"[INFO] Encoded {len(user_id_map)} users and {len(movie_id_map)} movies")
    
    return encoded_data, user_id_map, movie_id_map


def normalize_ratings(data, min_rating=0.5, max_rating=5.0):
    """Normalize ratings to [0, 1] range"""
    print("[INFO] Normalizing ratings...")
    
    normalized = data.copy()
    normalized['rating'] = (normalized['rating'] - min_rating) / (max_rating - min_rating)
    normalized['rating'] = normalized['rating'].clip(0.0, 1.0)
    
    print(f"[INFO] Normalized ratings to range [{normalized['rating'].min():.3f}, {normalized['rating'].max():.3f}]")
    
    return normalized


def split_data(data, train_ratio=0.8, val_ratio=0.1, test_ratio=0.1, random_state=42):
    """Split data into train/validation/test sets"""
    print("[INFO] Splitting data...")
    
    # Shuffle
    shuffled = data.sample(frac=1.0, random_state=random_state).reset_index(drop=True)
    
    # Calculate split sizes
    n = len(shuffled)
    train_size = int(n * train_ratio)
    val_size = int(n * val_ratio)
    
    # Split
    train_data = shuffled.iloc[:train_size]
    val_data = shuffled.iloc[train_size:train_size + val_size]
    test_data = shuffled.iloc[train_size + val_size:]
    
    print(f"[INFO] Train: {len(train_data)}, Val: {len(val_data)}, Test: {len(test_data)}")
    
    return train_data, val_data, test_data


def save_processed_data(train_data, val_data, test_data, output_path):
    """Save processed data to output directory"""
    print("[INFO] Saving processed data...")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)
    
    # Save as CSV files (only userId, movieId, rating columns)
    columns = ['userId', 'movieId', 'rating']
    
    train_file = os.path.join(output_path, 'train.csv')
    val_file = os.path.join(output_path, 'validation.csv')
    test_file = os.path.join(output_path, 'test.csv')
    
    train_data[columns].to_csv(train_file, index=False, header=True)
    val_data[columns].to_csv(val_file, index=False, header=True)
    test_data[columns].to_csv(test_file, index=False, header=True)
    
    print(f"[INFO] Saved train data to {train_file}")
    print(f"[INFO] Saved validation data to {val_file}")
    print(f"[INFO] Saved test data to {test_file}")
    
    # Verify files were created
    for file_path in [train_file, val_file, test_file]:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"[OK] {file_path} ({size} bytes)")
        else:
            print(f"[ERROR] Failed to create {file_path}")


def main():
    """Main preprocessing pipeline"""
    print("="*70)
    print("MOVIELENS DATA PREPROCESSING")
    print("="*70)
    
    # SageMaker paths
    input_path = '/opt/ml/processing/input'
    output_path = '/opt/ml/processing/output'
    
    print(f"[INFO] Input path: {input_path}")
    print(f"[INFO] Output path: {output_path}")
    
    try:
        # 1. Load data
        data = load_movielens_data(input_path)
        
        # 2. Clean data
        data = clean_data(data)
        
        # 3. Encode IDs
        data, user_map, movie_map = encode_ids(data)
        
        # 4. Normalize ratings
        data = normalize_ratings(data)
        
        # 5. Split data
        train_data, val_data, test_data = split_data(data)
        
        # 6. Save processed data
        save_processed_data(train_data, val_data, test_data, output_path)
        
        print("="*70)
        print("[OK] PREPROCESSING COMPLETE!")
        print("="*70)
        
    except Exception as e:
        print("="*70)
        print(f"[ERROR] PREPROCESSING FAILED: {e}")
        print("="*70)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
