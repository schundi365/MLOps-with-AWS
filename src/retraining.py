"""
Retraining utilities for scheduled model retraining.

This module provides functions to support automated retraining workflows,
including data selection logic to find the latest data in S3.
"""

import boto3
from typing import Optional, List, Dict
from datetime import datetime


def get_latest_data_path(
    bucket_name: str,
    prefix: str = "processed-data/",
    s3_client: Optional[boto3.client] = None
) -> str:
    """
    Find the latest data in S3 by sorting by timestamp and selecting most recent.
    
    This function lists all objects in the specified S3 bucket and prefix,
    sorts them by their LastModified timestamp, and returns the S3 URI
    of the most recent object.
    
    Args:
        bucket_name: Name of the S3 bucket
        prefix: S3 prefix/directory to search in (default: "processed-data/")
        s3_client: Optional boto3 S3 client (creates new one if not provided)
        
    Returns:
        S3 URI of the latest data file (e.g., "s3://bucket/processed-data/latest.csv")
        
    Raises:
        ValueError: If no data files are found in the specified location
        
    Example:
        >>> latest_path = get_latest_data_path("my-bucket", "processed-data/")
        >>> print(latest_path)
        s3://my-bucket/processed-data/2024-01-15/train.csv
    """
    if s3_client is None:
        s3_client = boto3.client('s3')
    
    # List all objects in the bucket with the given prefix
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
    except Exception as e:
        raise ValueError(f"Failed to list objects in s3://{bucket_name}/{prefix}: {str(e)}")
    
    # Check if any objects were found
    if 'Contents' not in response or len(response['Contents']) == 0:
        raise ValueError(f"No data files found in s3://{bucket_name}/{prefix}")
    
    # Sort objects by LastModified timestamp (most recent first)
    objects = response['Contents']
    sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)
    
    # Get the most recent object
    latest_object = sorted_objects[0]
    latest_key = latest_object['Key']
    
    # Return as S3 URI
    return f"s3://{bucket_name}/{latest_key}"


def get_latest_dataset_directory(
    bucket_name: str,
    prefix: str = "processed-data/",
    s3_client: Optional[boto3.client] = None
) -> str:
    """
    Find the latest dataset directory in S3 by timestamp.
    
    This function is useful when datasets are organized in dated directories
    (e.g., processed-data/2024-01-15/, processed-data/2024-01-16/).
    It returns the directory path of the most recent dataset.
    
    Args:
        bucket_name: Name of the S3 bucket
        prefix: S3 prefix to search in (default: "processed-data/")
        s3_client: Optional boto3 S3 client (creates new one if not provided)
        
    Returns:
        S3 URI of the latest dataset directory
        
    Raises:
        ValueError: If no directories are found
        
    Example:
        >>> latest_dir = get_latest_dataset_directory("my-bucket", "processed-data/")
        >>> print(latest_dir)
        s3://my-bucket/processed-data/2024-01-16/
    """
    if s3_client is None:
        s3_client = boto3.client('s3')
    
    # List all objects to find directories
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix,
            Delimiter='/'
        )
    except Exception as e:
        raise ValueError(f"Failed to list directories in s3://{bucket_name}/{prefix}: {str(e)}")
    
    # Get common prefixes (directories)
    if 'CommonPrefixes' not in response or len(response['CommonPrefixes']) == 0:
        raise ValueError(f"No directories found in s3://{bucket_name}/{prefix}")
    
    directories = [cp['Prefix'] for cp in response['CommonPrefixes']]
    
    # For each directory, get the latest modification time
    dir_timestamps: List[Dict] = []
    for directory in directories:
        try:
            dir_response = s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=directory,
                MaxKeys=1
            )
            if 'Contents' in dir_response and len(dir_response['Contents']) > 0:
                latest_modified = dir_response['Contents'][0]['LastModified']
                dir_timestamps.append({
                    'directory': directory,
                    'timestamp': latest_modified
                })
        except Exception:
            # Skip directories that can't be accessed
            continue
    
    if not dir_timestamps:
        raise ValueError(f"No accessible directories found in s3://{bucket_name}/{prefix}")
    
    # Sort by timestamp and get the most recent
    sorted_dirs = sorted(dir_timestamps, key=lambda x: x['timestamp'], reverse=True)
    latest_directory = sorted_dirs[0]['directory']
    
    return f"s3://{bucket_name}/{latest_directory}"


def list_data_files_by_timestamp(
    bucket_name: str,
    prefix: str = "processed-data/",
    s3_client: Optional[boto3.client] = None
) -> List[Dict[str, any]]:
    """
    List all data files in S3 sorted by timestamp (most recent first).
    
    Args:
        bucket_name: Name of the S3 bucket
        prefix: S3 prefix to search in (default: "processed-data/")
        s3_client: Optional boto3 S3 client (creates new one if not provided)
        
    Returns:
        List of dictionaries containing file information:
        - 'key': S3 object key
        - 'uri': Full S3 URI
        - 'last_modified': LastModified timestamp
        - 'size': File size in bytes
        
    Raises:
        ValueError: If no files are found
        
    Example:
        >>> files = list_data_files_by_timestamp("my-bucket", "processed-data/")
        >>> for file in files[:3]:  # Show top 3 most recent
        ...     print(f"{file['uri']} - {file['last_modified']}")
    """
    if s3_client is None:
        s3_client = boto3.client('s3')
    
    # List all objects
    try:
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
    except Exception as e:
        raise ValueError(f"Failed to list objects in s3://{bucket_name}/{prefix}: {str(e)}")
    
    if 'Contents' not in response or len(response['Contents']) == 0:
        raise ValueError(f"No files found in s3://{bucket_name}/{prefix}")
    
    # Sort by LastModified (most recent first)
    objects = response['Contents']
    sorted_objects = sorted(objects, key=lambda x: x['LastModified'], reverse=True)
    
    # Format results
    results = []
    for obj in sorted_objects:
        results.append({
            'key': obj['Key'],
            'uri': f"s3://{bucket_name}/{obj['Key']}",
            'last_modified': obj['LastModified'],
            'size': obj['Size']
        })
    
    return results
