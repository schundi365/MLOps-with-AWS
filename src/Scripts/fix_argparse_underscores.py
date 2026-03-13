#!/usr/bin/env python3
"""
Fix Issue #15: Argparse hyphen vs underscore mismatch.

Problem: SageMaker passes hyperparameters with underscores (--batch_size)
but argparse expects hyphens (--batch-size).

Solution: Update training script to accept both formats.
"""

import boto3
import tarfile
import io

def create_fixed_training_script():
    """Create training script that accepts both hyphens and underscores."""
    
    script_content = '''"""
SageMaker training script for collaborative filtering model.
Standalone version with model code embedded.
Fixed to accept both hyphens and underscores in arguments.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# MODEL DEFINITION (embedded)
# ============================================================================

class CollaborativeFilteringModel(nn.Module):
    """
    Collaborative filtering model using matrix factorization.
    
    The model learns embeddings for users and movies, along with bias terms,
    to predict ratings through dot product computation.
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


# ============================================================================
# DATASET
# ============================================================================

class RatingsDataset(Dataset):
    """PyTorch Dataset for user-movie ratings."""
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize dataset from DataFrame.
        
        Args:
            data: DataFrame with userId, movieId, and rating columns
        """
        self.user_ids = torch.LongTensor(data['userId'].values)
        self.movie_ids = torch.LongTensor(data['movieId'].values)
        self.ratings = torch.FloatTensor(data['rating'].values)
    
    def __len__(self) -> int:
        return len(self.ratings)
    
    def __getitem__(self, idx: int) -> tuple:
        return self.user_ids[idx], self.movie_ids[idx], self.ratings[idx]


# ============================================================================
# TRAINING FUNCTIONS
# ============================================================================

def parse_args():
    """Parse command-line arguments for training hyperparameters."""
    parser = argparse.ArgumentParser(description='Train collaborative filtering model')
    
    # Hyperparameters - accept BOTH hyphens and underscores
    parser.add_argument('--embedding-dim', '--embedding_dim', type=int, default=128, dest='embedding_dim',
                        help='Dimensionality of user and movie embeddings (default: 128)')
    parser.add_argument('--learning-rate', '--learning_rate', type=float, default=0.001, dest='learning_rate',
                        help='Learning rate for Adam optimizer (default: 0.001)')
    parser.add_argument('--batch-size', '--batch_size', type=int, default=256, dest='batch_size',
                        help='Training batch size (default: 256)')
    parser.add_argument('--epochs', type=int, default=50,
                        help='Number of training epochs (default: 50)')
    parser.add_argument('--num-factors', '--num_factors', type=int, default=50, dest='num_factors',
                        help='Number of latent factors (alias for embedding-dim, default: 50)')
    
    # SageMaker-specific arguments
    parser.add_argument('--model-dir', '--model_dir', type=str, default=os.environ.get('SM_MODEL_DIR', './model'), dest='model_dir')
    parser.add_argument('--train', type=str, default=os.environ.get('SM_CHANNEL_TRAIN', './data/train'))
    parser.add_argument('--validation', type=str, default=os.environ.get('SM_CHANNEL_VALIDATION', './data/validation'))
    parser.add_argument('--output-data-dir', '--output_data_dir', type=str, default=os.environ.get('SM_OUTPUT_DATA_DIR', './output'), dest='output_data_dir')
    
    # Device configuration
    parser.add_argument('--num-gpus', '--num_gpus', type=int, default=torch.cuda.device_count(), dest='num_gpus')
    
    args = parser.parse_args()
    
    # Use num_factors if provided, otherwise use embedding_dim
    if args.num_factors != 50:  # If num_factors was explicitly set
        args.embedding_dim = args.num_factors
    
    return args


def load_data(data_dir: str) -> pd.DataFrame:
    """Load data from SageMaker input channel."""
    logger.info(f"Loading data from {data_dir}")
    
    # Find CSV files in the directory
    data_path = Path(data_dir)
    csv_files = list(data_path.glob('*.csv'))
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")
    
    # Load the first CSV file (assuming single file per channel)
    data_file = csv_files[0]
    logger.info(f"Loading data from {data_file}")
    
    data = pd.read_csv(data_file)
    
    # Validate required columns
    required_columns = ['userId', 'movieId', 'rating']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    logger.info(f"Loaded {len(data)} samples")
    return data


def train_epoch(model: nn.Module, train_loader: DataLoader, 
                criterion: nn.Module, optimizer: optim.Optimizer,
                device: torch.device) -> float:
    """Train model for one epoch."""
    model.train()
    total_loss = 0.0
    total_samples = 0
    
    for user_ids, movie_ids, ratings in train_loader:
        # Move data to device
        user_ids = user_ids.to(device)
        movie_ids = movie_ids.to(device)
        ratings = ratings.to(device)
        
        # Zero gradients
        optimizer.zero_grad()
        
        # Forward pass
        predictions = model(user_ids, movie_ids)
        
        # Calculate loss
        loss = criterion(predictions, ratings)
        
        # Backward pass
        loss.backward()
        
        # Update weights
        optimizer.step()
        
        # Accumulate loss
        total_loss += loss.item() * len(ratings)
        total_samples += len(ratings)
    
    # Calculate average MSE and convert to RMSE
    avg_mse = total_loss / total_samples
    avg_rmse = np.sqrt(avg_mse)
    
    return avg_rmse


def validate(model: nn.Module, val_loader: DataLoader,
             criterion: nn.Module, device: torch.device) -> float:
    """Validate model on validation set."""
    model.eval()
    total_loss = 0.0
    total_samples = 0
    
    with torch.no_grad():
        for user_ids, movie_ids, ratings in val_loader:
            # Move data to device
            user_ids = user_ids.to(device)
            movie_ids = movie_ids.to(device)
            ratings = ratings.to(device)
            
            # Forward pass
            predictions = model(user_ids, movie_ids)
            
            # Calculate loss
            loss = criterion(predictions, ratings)
            
            # Accumulate loss
            total_loss += loss.item() * len(ratings)
            total_samples += len(ratings)
    
    # Calculate average MSE and convert to RMSE
    avg_mse = total_loss / total_samples
    avg_rmse = np.sqrt(avg_mse)
    
    return avg_rmse


def save_checkpoint(model: nn.Module, optimizer: optim.Optimizer,
                   epoch: int, val_rmse: float, checkpoint_path: str):
    """Save model checkpoint."""
    checkpoint = {
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'val_rmse': val_rmse
    }
    torch.save(checkpoint, checkpoint_path)
    logger.info(f"Saved checkpoint to {checkpoint_path}")


def save_model(model: nn.Module, model_dir: str, num_users: int,
               num_movies: int, embedding_dim: int, metadata: dict):
    """Save final model to SageMaker model directory."""
    # Create model directory if it doesn't exist
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model state dict
    model_path = os.path.join(model_dir, 'model.pth')
    torch.save(model.state_dict(), model_path)
    logger.info(f"Saved model to {model_path}")
    
    # Save metadata
    metadata_dict = {
        'num_users': int(num_users),
        'num_movies': int(num_movies),
        'embedding_dim': int(embedding_dim),
        **metadata
    }
    metadata_path = os.path.join(model_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata_dict, f, indent=2)
    logger.info(f"Saved metadata to {metadata_path}")


def train(args):
    """Main training function."""
    logger.info("Starting training")
    logger.info(f"Arguments: {args}")
    
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() and args.num_gpus > 0 else 'cpu')
    logger.info(f"Using device: {device}")
    
    # Load data
    logger.info("Loading training data")
    train_data = load_data(args.train)
    
    logger.info("Loading validation data")
    val_data = load_data(args.validation)
    
    # Get number of unique users and movies
    num_users = max(train_data['userId'].max(), val_data['userId'].max()) + 1
    num_movies = max(train_data['movieId'].max(), val_data['movieId'].max()) + 1
    
    logger.info(f"Number of users: {num_users}")
    logger.info(f"Number of movies: {num_movies}")
    
    # Create datasets and dataloaders
    train_dataset = RatingsDataset(train_data)
    val_dataset = RatingsDataset(val_data)
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0  # Set to 0 for compatibility
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0
    )
    
    # Create model
    logger.info(f"Creating model with embedding_dim={args.embedding_dim}")
    model = CollaborativeFilteringModel(
        num_users=num_users,
        num_movies=num_movies,
        embedding_dim=args.embedding_dim
    )
    model = model.to(device)
    
    # Create loss function and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)
    
    # Training loop
    best_val_rmse = float('inf')
    best_epoch = 0
    
    logger.info("Starting training loop")
    for epoch in range(1, args.epochs + 1):
        # Train for one epoch
        train_rmse = train_epoch(model, train_loader, criterion, optimizer, device)
        
        # Validate
        val_rmse = validate(model, val_loader, criterion, device)
        
        # Log metrics (CloudWatch will capture these)
        logger.info(f"Epoch {epoch}/{args.epochs} - Train RMSE: {train_rmse:.4f} - Val RMSE: {val_rmse:.4f}")
        
        # Save checkpoint if best model
        if val_rmse < best_val_rmse:
            best_val_rmse = val_rmse
            best_epoch = epoch
            
            # Save checkpoint
            checkpoint_path = os.path.join(args.output_data_dir, 'best_checkpoint.pth')
            os.makedirs(args.output_data_dir, exist_ok=True)
            save_checkpoint(model, optimizer, epoch, val_rmse, checkpoint_path)
            
            logger.info(f"New best model at epoch {epoch} with Val RMSE: {val_rmse:.4f}")
    
    # Log final results
    logger.info(f"Training completed. Best Val RMSE: {best_val_rmse:.4f} at epoch {best_epoch}")
    
    # Save final model
    metadata = {
        'training_rmse': float(train_rmse),
        'validation_rmse': float(best_val_rmse),
        'best_epoch': int(best_epoch),
        'hyperparameters': {
            'learning_rate': float(args.learning_rate),
            'batch_size': int(args.batch_size),
            'epochs': int(args.epochs),
            'embedding_dim': int(args.embedding_dim)
        }
    }
    
    save_model(model, args.model_dir, num_users, num_movies, args.embedding_dim, metadata)
    
    logger.info("Training script completed successfully")


if __name__ == '__main__':
    args = parse_args()
    train(args)
'''
    
    return script_content


def main():
    """Main function to fix the argparse issue."""
    
    bucket_name = 'amzn-s3-movielens-327030626634'
    region = 'us-east-1'
    
    print("\n" + "="*70)
    print("FIXING ISSUE #15: Argparse Hyphen vs Underscore")
    print("="*70)
    print()
    
    # Create fixed training script
    print("Creating fixed training script...")
    train_script = create_fixed_training_script()
    
    # Create tarball in memory
    print("Creating tarball...")
    tarball_buffer = io.BytesIO()
    with tarfile.open(fileobj=tarball_buffer, mode='w:gz') as tar:
        # Add train.py
        train_info = tarfile.TarInfo(name='train.py')
        train_info.size = len(train_script.encode('utf-8'))
        tar.addfile(train_info, io.BytesIO(train_script.encode('utf-8')))
    
    tarball_buffer.seek(0)
    tarball_size = len(tarball_buffer.getvalue())
    
    print(f"Tarball size: {tarball_size:,} bytes")
    
    # Upload to S3
    print(f"Uploading to s3://{bucket_name}/code/sourcedir.tar.gz...")
    s3 = boto3.client('s3', region_name=region)
    s3.put_object(
        Bucket=bucket_name,
        Key='code/sourcedir.tar.gz',
        Body=tarball_buffer.getvalue()
    )
    
    print("[OK] Tarball uploaded successfully")
    print()
    print("="*70)
    print("FIX APPLIED")
    print("="*70)
    print()
    print("Changes made:")
    print("1. Updated argparse to accept BOTH hyphens and underscores")
    print("2. --batch-size and --batch_size both work now")
    print("3. --learning-rate and --learning_rate both work now")
    print("4. --embedding-dim and --embedding_dim both work now")
    print()
    print("This fixes the mismatch between SageMaker's hyperparameter format")
    print("(underscores) and argparse's expected format (hyphens).")
    print()
    print("Next step: Restart the pipeline")
    print("  python start_pipeline.py --region us-east-1")
    print()
    print("="*70)


if __name__ == "__main__":
    main()
