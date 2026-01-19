"""
Data Upload Utility for MovieLens Dataset

This script downloads the MovieLens dataset and uploads it to S3.
Supports both MovieLens 25M and 100K datasets.
"""

import argparse
import hashlib
import os
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError


# MovieLens dataset URLs and checksums
MOVIELENS_DATASETS = {
    "100k": {
        "url": "https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
        "files": ["movies.csv", "ratings.csv", "tags.csv", "links.csv"],
        "description": "MovieLens Latest Small (100K ratings)"
    },
    "25m": {
        "url": "https://files.grouplens.org/datasets/movielens/ml-25m.zip",
        "files": ["movies.csv", "ratings.csv", "tags.csv", "links.csv", "genome-scores.csv", "genome-tags.csv"],
        "description": "MovieLens 25M"
    }
}


def download_file(url: str, destination: Path) -> None:
    """
    Download a file from URL to destination path.
    
    Args:
        url: URL to download from
        destination: Local path to save file
    """
    print(f"Downloading from {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            chunk_size = 8192
            
            with open(destination, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Show progress
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}% ({downloaded}/{total_size} bytes)", end='')
            
            print()  # New line after progress
            print(f"Download complete: {destination}")
    except Exception as e:
        raise RuntimeError(f"Failed to download file: {e}")


def calculate_md5(file_path: Path) -> str:
    """
    Calculate MD5 checksum of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        MD5 checksum as hex string
    """
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def extract_zip(zip_path: Path, extract_to: Path) -> Path:
    """
    Extract ZIP file to destination directory.
    
    Args:
        zip_path: Path to ZIP file
        extract_to: Directory to extract to
        
    Returns:
        Path to extracted directory
    """
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    
    # Find the extracted directory (usually has a single top-level directory)
    extracted_dirs = [d for d in extract_to.iterdir() if d.is_dir()]
    if len(extracted_dirs) == 1:
        extracted_dir = extracted_dirs[0]
    else:
        extracted_dir = extract_to
    
    print(f"Extracted to: {extracted_dir}")
    return extracted_dir


def verify_files(directory: Path, expected_files: list) -> bool:
    """
    Verify that all expected files exist in the directory.
    
    Args:
        directory: Directory to check
        expected_files: List of expected file names
        
    Returns:
        True if all files exist, False otherwise
    """
    print("Verifying files...")
    missing_files = []
    
    for file_name in expected_files:
        file_path = directory / file_name
        if not file_path.exists():
            missing_files.append(file_name)
            print(f"  [X] Missing: {file_name}")
        else:
            file_size = file_path.stat().st_size
            print(f"  [OK] Found: {file_name} ({file_size:,} bytes)")
    
    if missing_files:
        print(f"\nError: Missing files: {', '.join(missing_files)}")
        return False
    
    print("All files verified successfully!")
    return True


def upload_to_s3(local_dir: Path, bucket_name: str, s3_prefix: str, files: list) -> None:
    """
    Upload files to S3 bucket.
    
    Args:
        local_dir: Local directory containing files
        bucket_name: S3 bucket name
        s3_prefix: S3 key prefix (e.g., 'raw-data/')
        files: List of file names to upload
    """
    print(f"\nUploading to S3 bucket: {bucket_name}")
    print(f"S3 prefix: {s3_prefix}")
    
    s3_client = boto3.client('s3')
    
    # Check if bucket exists
    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            raise RuntimeError(f"Bucket '{bucket_name}' does not exist. Please create it first.")
        elif error_code == '403':
            raise RuntimeError(f"Access denied to bucket '{bucket_name}'. Check your AWS credentials and permissions.")
        else:
            raise RuntimeError(f"Error accessing bucket: {e}")
    
    uploaded_files = []
    for file_name in files:
        local_path = local_dir / file_name
        if not local_path.exists():
            print(f"  [!] Skipping {file_name} (not found)")
            continue
        
        s3_key = f"{s3_prefix}{file_name}"
        
        try:
            # Calculate MD5 for integrity check
            md5_checksum = calculate_md5(local_path)
            
            # Upload file
            print(f"  Uploading {file_name}...")
            s3_client.upload_file(
                str(local_path),
                bucket_name,
                s3_key,
                ExtraArgs={'Metadata': {'md5': md5_checksum}}
            )
            
            # Verify upload
            response = s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            s3_size = response['ContentLength']
            local_size = local_path.stat().st_size
            
            if s3_size == local_size:
                print(f"  [OK] Uploaded: s3://{bucket_name}/{s3_key} ({s3_size:,} bytes)")
                uploaded_files.append(file_name)
            else:
                print(f"  [X] Size mismatch for {file_name}: local={local_size}, s3={s3_size}")
        
        except ClientError as e:
            print(f"  [X] Failed to upload {file_name}: {e}")
            raise
    
    print(f"\nSuccessfully uploaded {len(uploaded_files)} files to S3")


def main():
    """Main function to download and upload MovieLens data."""
    parser = argparse.ArgumentParser(
        description="Download MovieLens dataset and upload to S3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download 100K dataset and upload to S3
  python data_upload.py --dataset 100k --bucket my-bucket --prefix raw-data/
  
  # Download 25M dataset
  python data_upload.py --dataset 25m --bucket my-bucket --prefix raw-data/
  
  # Use existing local files (skip download)
  python data_upload.py --local-dir /path/to/data --bucket my-bucket --prefix raw-data/
        """
    )
    
    parser.add_argument(
        '--dataset',
        choices=['100k', '25m'],
        help='MovieLens dataset version to download (100k or 25m)'
    )
    parser.add_argument(
        '--bucket',
        required=True,
        help='S3 bucket name'
    )
    parser.add_argument(
        '--prefix',
        default='raw-data/',
        help='S3 key prefix (default: raw-data/)'
    )
    parser.add_argument(
        '--local-dir',
        type=Path,
        help='Use existing local directory instead of downloading'
    )
    parser.add_argument(
        '--keep-local',
        action='store_true',
        help='Keep downloaded files after upload (default: delete)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.local_dir and not args.dataset:
        parser.error("Either --dataset or --local-dir must be specified")
    
    # Ensure prefix ends with /
    if args.prefix and not args.prefix.endswith('/'):
        args.prefix += '/'
    
    try:
        if args.local_dir:
            # Use existing local directory
            if not args.local_dir.exists():
                print(f"Error: Local directory does not exist: {args.local_dir}")
                sys.exit(1)
            
            data_dir = args.local_dir
            # Assume all CSV files in directory
            files_to_upload = [f.name for f in data_dir.glob("*.csv")]
            
            if not files_to_upload:
                print(f"Error: No CSV files found in {data_dir}")
                sys.exit(1)
            
            print(f"Using local directory: {data_dir}")
            print(f"Found {len(files_to_upload)} CSV files")
        
        else:
            # Download dataset
            dataset_info = MOVIELENS_DATASETS[args.dataset]
            print(f"Dataset: {dataset_info['description']}")
            
            # Create temporary directory
            temp_dir = Path(tempfile.mkdtemp(prefix='movielens_'))
            print(f"Working directory: {temp_dir}")
            
            try:
                # Download ZIP file
                zip_path = temp_dir / "movielens.zip"
                download_file(dataset_info['url'], zip_path)
                
                # Extract ZIP
                extract_dir = temp_dir / "extracted"
                extract_dir.mkdir(exist_ok=True)
                data_dir = extract_zip(zip_path, extract_dir)
                
                # Verify files
                if not verify_files(data_dir, dataset_info['files']):
                    sys.exit(1)
                
                files_to_upload = dataset_info['files']
            
            except Exception as e:
                print(f"\nError during download/extraction: {e}")
                sys.exit(1)
        
        # Upload to S3
        upload_to_s3(data_dir, args.bucket, args.prefix, files_to_upload)
        
        # Cleanup
        if not args.local_dir and not args.keep_local:
            print("\nCleaning up temporary files...")
            import shutil
            shutil.rmtree(temp_dir)
            print("Cleanup complete")
        
        print("\n[OK] Data upload completed successfully!")
        print(f"Files are available at: s3://{args.bucket}/{args.prefix}")
    
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
