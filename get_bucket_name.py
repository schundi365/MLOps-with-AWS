"""Get the actual S3 bucket name."""

import boto3

s3_client = boto3.client('s3', region_name='us-east-1')

# List buckets
response = s3_client.list_buckets()

print("\nS3 Buckets:")
for bucket in response['Buckets']:
    if 'movielens' in bucket['Name'].lower():
        print(f"  - {bucket['Name']}")
