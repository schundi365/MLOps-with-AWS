"""
SageMaker training script for collaborative filtering model.

This script handles model training on SageMaker, including:
- Argument parsing for hyperparameters
- Data loading from SageMaker input channels
- Training loop with MSE loss
- Validation loop
- RMSE logging for CloudWatch
- Model checkpointing
- Saving final model to SageMaker model directory

Validates: Requirements 3.4, 3.5, 3.6
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

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent))
from model import CollaborativeFilteringModel


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


def parse_args():
    """
    Parse command-line arguments for training hyperparameters.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(description='Train collaborative filtering model')
    
    # Hyperparameters
    parser.add_argument('--embedding-dim', type=int, default=128,
                        help='Dimensionality of user and movie embeddings (default: 128)')
    parser.add_argument('--learning-rate', type=float, default=0.001,
                        help='Learning rate for Adam optimizer (default: 0.001)')
    parser.add_argument('--batch-size', type=int, default=256,
                        help='Training batch size (default: 256)')
    parser.add_argument('--epochs', type=int, default=50,
                        help='Number of training epochs (default: 50)')
    parser.add_argument('--num-factors', type=int, default=50,
                        help='Number of latent factors (alias for embedding-dim, default: 50)')
    
    # SageMaker-specific arguments
    parser.add_argument('--model-dir', type=str, default=os.environ.get('SM_MODEL_DIR', './model'))
    parser.add_argument('--train', type=str, default=os.environ.get('SM_CHANNEL_TRAIN', './data/train'))
    parser.add_argument('--validation', type=str, default=os.environ.get('SM_CHANNEL_VALIDATION', './data/validation'))
    parser.add_argument('--output-data-dir', type=str, default=os.environ.get('SM_OUTPUT_DATA_DIR', './output'))
    
    # Device configuration
    parser.add_argument('--num-gpus', type=int, default=torch.cuda.device_count())
    
    args = parser.parse_args()
    
    # Use num_factors if provided, otherwise use embedding_dim
    if args.num_factors != 50:  # If num_factors was explicitly set
        args.embedding_dim = args.num_factors
    
    return args


def load_data(data_dir: str) -> pd.DataFrame:
    """
    Load data from SageMaker input channel.
    
    Args:
        data_dir: Directory containing CSV files
    
    Returns:
        DataFrame with userId, movieId, and rating columns
    """
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


def calculate_rmse(predictions: torch.Tensor, targets: torch.Tensor) -> float:
    """
    Calculate Root Mean Square Error.
    
    Args:
        predictions: Predicted ratings
        targets: Actual ratings
    
    Returns:
        RMSE value
    """
    mse = torch.mean((predictions - targets) ** 2)
    rmse = torch.sqrt(mse)
    return rmse.item()


def train_epoch(model: nn.Module, train_loader: DataLoader, 
                criterion: nn.Module, optimizer: optim.Optimizer,
                device: torch.device) -> float:
    """
    Train model for one epoch.
    
    Args:
        model: Collaborative filtering model
        train_loader: DataLoader for training data
        criterion: Loss function (MSE)
        optimizer: Optimizer
        device: Device to train on (CPU or GPU)
    
    Returns:
        Average training RMSE for the epoch
    """
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
    """
    Validate model on validation set.
    
    Args:
        model: Collaborative filtering model
        val_loader: DataLoader for validation data
        criterion: Loss function (MSE)
        device: Device to validate on (CPU or GPU)
    
    Returns:
        Validation RMSE
    """
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
    """
    Save model checkpoint.
    
    Args:
        model: Model to save
        optimizer: Optimizer state to save
        epoch: Current epoch number
        val_rmse: Validation RMSE at this checkpoint
        checkpoint_path: Path to save checkpoint
    """
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
    """
    Save final model to SageMaker model directory.
    
    Args:
        model: Trained model
        model_dir: Directory to save model
        num_users: Number of users in training data
        num_movies: Number of movies in training data
        embedding_dim: Embedding dimensionality
        metadata: Additional metadata to save
    """
    # Create model directory if it doesn't exist
    os.makedirs(model_dir, exist_ok=True)
    
    # Save model state dict
    model_path = os.path.join(model_dir, 'model.pth')
    torch.save(model.state_dict(), model_path)
    logger.info(f"Saved model to {model_path}")
    
    # Save metadata
    # Convert numpy types to native Python types for JSON serialization
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
    """
    Main training function.
    
    Args:
        args: Parsed command-line arguments
    """
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
        'training_rmse': train_rmse,
        'validation_rmse': best_val_rmse,
        'best_epoch': best_epoch,
        'hyperparameters': {
            'learning_rate': args.learning_rate,
            'batch_size': args.batch_size,
            'epochs': args.epochs,
            'embedding_dim': args.embedding_dim
        }
    }
    
    save_model(model, args.model_dir, num_users, num_movies, args.embedding_dim, metadata)
    
    logger.info("Training script completed successfully")


if __name__ == '__main__':
    args = parse_args()
    train(args)
