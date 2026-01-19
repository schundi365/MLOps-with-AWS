# MovieLens Data Upload Utility

This utility downloads the MovieLens dataset and uploads it to an S3 bucket for use in the recommendation system.

## Prerequisites

- Python 3.10+
- AWS credentials configured (via `aws configure` or environment variables)
- S3 bucket created (see `src/infrastructure/s3_setup.py`)

## Installation

Install required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Download and Upload MovieLens 100K Dataset

```bash
python src/data_upload.py --dataset 100k --bucket movielens-recommendation-bucket --prefix raw-data/
```

### Download and Upload MovieLens 25M Dataset

```bash
python src/data_upload.py --dataset 25m --bucket movielens-recommendation-bucket --prefix raw-data/
```

### Upload Existing Local Files

If you already have the MovieLens data downloaded locally:

```bash
python src/data_upload.py --local-dir /path/to/movielens/data --bucket movielens-recommendation-bucket --prefix raw-data/
```

### Keep Local Files After Upload

By default, downloaded files are deleted after upload. To keep them:

```bash
python src/data_upload.py --dataset 100k --bucket movielens-recommendation-bucket --prefix raw-data/ --keep-local
```

## Command-Line Options

- `--dataset {100k,25m}`: MovieLens dataset version to download (required unless using `--local-dir`)
- `--bucket BUCKET`: S3 bucket name (required)
- `--prefix PREFIX`: S3 key prefix (default: `raw-data/`)
- `--local-dir LOCAL_DIR`: Use existing local directory instead of downloading
- `--keep-local`: Keep downloaded files after upload (default: delete)

## What It Does

1. **Downloads** the specified MovieLens dataset from GroupLens
2. **Extracts** the ZIP archive
3. **Verifies** that all required CSV files are present
4. **Calculates** MD5 checksums for file integrity
5. **Uploads** files to S3 with metadata
6. **Verifies** successful upload by checking file sizes
7. **Cleans up** temporary files (unless `--keep-local` is specified)

## Dataset Information

### MovieLens 100K (Latest Small)
- **Size**: ~1 MB
- **Ratings**: ~100,000
- **Files**: movies.csv, ratings.csv, tags.csv, links.csv
- **Best for**: Testing and development

### MovieLens 25M
- **Size**: ~250 MB
- **Ratings**: ~25 million
- **Files**: movies.csv, ratings.csv, tags.csv, links.csv, genome-scores.csv, genome-tags.csv
- **Best for**: Production training

## File Integrity

The utility:
- Calculates MD5 checksums for all uploaded files
- Stores checksums in S3 object metadata
- Verifies file sizes match between local and S3
- Reports any mismatches or errors

## Error Handling

The script handles common errors:
- **Bucket not found**: Ensure the S3 bucket exists
- **Access denied**: Check AWS credentials and IAM permissions
- **Download failures**: Network issues or invalid URLs
- **Missing files**: Incomplete dataset extraction

## Example Output

```
Dataset: MovieLens Latest Small (100K ratings)
Working directory: /tmp/movielens_abc123
Downloading from https://files.grouplens.org/datasets/movielens/ml-latest-small.zip...
Progress: 100.0% (955024/955024 bytes)
Download complete: /tmp/movielens_abc123/movielens.zip
Extracting /tmp/movielens_abc123/movielens.zip...
Extracted to: /tmp/movielens_abc123/extracted/ml-latest-small
Verifying files...
  ✓ Found: movies.csv (494,430 bytes)
  ✓ Found: ratings.csv (2,493,747 bytes)
  ✓ Found: tags.csv (47,957 bytes)
  ✓ Found: links.csv (172,710 bytes)
All files verified successfully!

Uploading to S3 bucket: movielens-recommendation-bucket
S3 prefix: raw-data/
  Uploading movies.csv...
  ✓ Uploaded: s3://movielens-recommendation-bucket/raw-data/movies.csv (494,430 bytes)
  Uploading ratings.csv...
  ✓ Uploaded: s3://movielens-recommendation-bucket/raw-data/ratings.csv (2,493,747 bytes)
  Uploading tags.csv...
  ✓ Uploaded: s3://movielens-recommendation-bucket/raw-data/tags.csv (47,957 bytes)
  Uploading links.csv...
  ✓ Uploaded: s3://movielens-recommendation-bucket/raw-data/links.csv (172,710 bytes)

Successfully uploaded 4 files to S3

Cleaning up temporary files...
Cleanup complete

✓ Data upload completed successfully!
Files are available at: s3://movielens-recommendation-bucket/raw-data/
```

## Integration with Pipeline

After uploading data, you can run the preprocessing step:

```bash
# Using SageMaker Processing
python src/infrastructure/sagemaker_deployment.py --action create-processing-job
```

Or run the complete pipeline:

```bash
# Using Step Functions
python src/infrastructure/stepfunctions_deployment.py --action start-execution
```

## Troubleshooting

### "Bucket does not exist"
Create the S3 bucket first:
```bash
python src/infrastructure/s3_setup.py
```

### "Access denied"
Ensure your AWS credentials have the necessary permissions:
- `s3:PutObject`
- `s3:GetObject`
- `s3:HeadBucket`
- `s3:HeadObject`

### "Download failed"
Check your internet connection and verify the GroupLens URLs are accessible.

## Testing

Run unit tests:

```bash
pytest tests/unit/test_data_upload.py -v
```

## Requirements Validation

This utility satisfies:
- **Requirement 1.1**: Downloads MovieLens dataset (25M or 100K version)
- **Requirement 1.3**: Stores raw data files in S3 raw-data directory with verification
