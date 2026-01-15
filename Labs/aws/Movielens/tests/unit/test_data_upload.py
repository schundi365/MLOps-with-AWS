"""
Unit tests for data upload utility
"""

import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.data_upload import (
    calculate_md5,
    verify_files,
    MOVIELENS_DATASETS
)


class TestDataUpload:
    """Test data upload utility functions"""
    
    def test_calculate_md5(self):
        """Test MD5 checksum calculation"""
        # Create a temporary file with known content
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test content")
            temp_path = Path(f.name)
        
        try:
            # Calculate MD5
            md5 = calculate_md5(temp_path)
            
            # Verify it's a valid MD5 hash (32 hex characters)
            assert len(md5) == 32
            assert all(c in '0123456789abcdef' for c in md5)
            
            # Verify it matches expected value
            expected_md5 = hashlib.md5(b"test content").hexdigest()
            assert md5 == expected_md5
        
        finally:
            temp_path.unlink()
    
    def test_verify_files_all_present(self):
        """Test file verification when all files are present"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            expected_files = ["movies.csv", "ratings.csv", "tags.csv"]
            for file_name in expected_files:
                (temp_path / file_name).write_text("test data")
            
            # Verify files
            result = verify_files(temp_path, expected_files)
            assert result is True
    
    def test_verify_files_missing(self):
        """Test file verification when files are missing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create only some files
            (temp_path / "movies.csv").write_text("test data")
            
            # Verify files (should fail)
            expected_files = ["movies.csv", "ratings.csv", "tags.csv"]
            result = verify_files(temp_path, expected_files)
            assert result is False
    
    def test_verify_files_empty_directory(self):
        """Test file verification with empty directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Verify files (should fail)
            expected_files = ["movies.csv"]
            result = verify_files(temp_path, expected_files)
            assert result is False
    
    def test_movielens_datasets_structure(self):
        """Test that MOVIELENS_DATASETS has correct structure"""
        assert "100k" in MOVIELENS_DATASETS
        assert "25m" in MOVIELENS_DATASETS
        
        for dataset_key, dataset_info in MOVIELENS_DATASETS.items():
            assert "url" in dataset_info
            assert "files" in dataset_info
            assert "description" in dataset_info
            assert isinstance(dataset_info["files"], list)
            assert len(dataset_info["files"]) > 0
            assert dataset_info["url"].startswith("https://")
    
    def test_movielens_100k_files(self):
        """Test that 100K dataset has required files"""
        dataset_info = MOVIELENS_DATASETS["100k"]
        required_files = ["movies.csv", "ratings.csv", "tags.csv", "links.csv"]
        
        for file_name in required_files:
            assert file_name in dataset_info["files"]
    
    def test_movielens_25m_files(self):
        """Test that 25M dataset has required files"""
        dataset_info = MOVIELENS_DATASETS["25m"]
        required_files = ["movies.csv", "ratings.csv", "tags.csv", "links.csv"]
        
        for file_name in required_files:
            assert file_name in dataset_info["files"]
    
    @patch('src.data_upload.boto3.client')
    def test_upload_to_s3_bucket_not_found(self, mock_boto_client):
        """Test error handling when S3 bucket doesn't exist"""
        from botocore.exceptions import ClientError
        from src.data_upload import upload_to_s3
        
        # Mock S3 client to raise 404 error
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        error_response = {'Error': {'Code': '404'}}
        mock_s3.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "test.csv").write_text("test")
            
            with pytest.raises(RuntimeError, match="does not exist"):
                upload_to_s3(temp_path, "nonexistent-bucket", "raw-data/", ["test.csv"])
    
    @patch('src.data_upload.boto3.client')
    def test_upload_to_s3_access_denied(self, mock_boto_client):
        """Test error handling when access is denied to S3 bucket"""
        from botocore.exceptions import ClientError
        from src.data_upload import upload_to_s3
        
        # Mock S3 client to raise 403 error
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        error_response = {'Error': {'Code': '403'}}
        mock_s3.head_bucket.side_effect = ClientError(error_response, 'HeadBucket')
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "test.csv").write_text("test")
            
            with pytest.raises(RuntimeError, match="Access denied"):
                upload_to_s3(temp_path, "forbidden-bucket", "raw-data/", ["test.csv"])
    
    @patch('src.data_upload.boto3.client')
    def test_upload_to_s3_correct_paths(self, mock_boto_client):
        """Test file upload to correct S3 paths"""
        from src.data_upload import upload_to_s3
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock successful bucket check
        mock_s3.head_bucket.return_value = {}
        
        # Mock successful upload and head_object
        mock_s3.upload_file.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test files
            test_files = ["movies.csv", "ratings.csv", "tags.csv"]
            for file_name in test_files:
                file_path = temp_path / file_name
                file_path.write_text("test data")
                
                # Mock head_object to return correct size
                file_size = file_path.stat().st_size
                mock_s3.head_object.return_value = {'ContentLength': file_size}
            
            # Upload files
            bucket_name = "test-bucket"
            s3_prefix = "raw-data/"
            upload_to_s3(temp_path, bucket_name, s3_prefix, test_files)
            
            # Verify upload_file was called with correct paths
            assert mock_s3.upload_file.call_count == len(test_files)
            
            for i, file_name in enumerate(test_files):
                call_args = mock_s3.upload_file.call_args_list[i]
                local_path = str(temp_path / file_name)
                expected_s3_key = f"{s3_prefix}{file_name}"
                
                # Check arguments: (local_path, bucket, s3_key, ExtraArgs)
                assert call_args[0][0] == local_path
                assert call_args[0][1] == bucket_name
                assert call_args[0][2] == expected_s3_key
                
                # Verify MD5 metadata was included
                assert 'ExtraArgs' in call_args[1]
                assert 'Metadata' in call_args[1]['ExtraArgs']
                assert 'md5' in call_args[1]['ExtraArgs']['Metadata']
    
    @patch('src.data_upload.boto3.client')
    def test_upload_to_s3_with_different_prefix(self, mock_boto_client):
        """Test file upload with different S3 prefix"""
        from src.data_upload import upload_to_s3
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock successful operations
        mock_s3.head_bucket.return_value = {}
        mock_s3.upload_file.return_value = None
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file
            test_file = "test.csv"
            file_path = temp_path / test_file
            file_path.write_text("test data")
            
            # Mock head_object
            mock_s3.head_object.return_value = {'ContentLength': file_path.stat().st_size}
            
            # Upload with custom prefix
            bucket_name = "test-bucket"
            s3_prefix = "processed-data/2024/"
            upload_to_s3(temp_path, bucket_name, s3_prefix, [test_file])
            
            # Verify correct S3 key was used
            call_args = mock_s3.upload_file.call_args
            expected_s3_key = f"{s3_prefix}{test_file}"
            assert call_args[0][2] == expected_s3_key
    
    @patch('src.data_upload.urllib.request.urlopen')
    def test_download_file_network_error(self, mock_urlopen):
        """Test error handling for network issues during download"""
        from src.data_upload import download_file
        import urllib.error
        
        # Mock network error
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "test.zip"
            
            with pytest.raises(RuntimeError, match="Failed to download file"):
                download_file("https://example.com/test.zip", temp_path)
    
    @patch('src.data_upload.urllib.request.urlopen')
    def test_download_file_http_error(self, mock_urlopen):
        """Test error handling for HTTP errors during download"""
        from src.data_upload import download_file
        import urllib.error
        
        # Mock HTTP 404 error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://example.com/test.zip", 404, "Not Found", {}, None
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "test.zip"
            
            with pytest.raises(RuntimeError, match="Failed to download file"):
                download_file("https://example.com/test.zip", temp_path)
    
    @patch('src.data_upload.urllib.request.urlopen')
    def test_download_file_timeout(self, mock_urlopen):
        """Test error handling for timeout during download"""
        from src.data_upload import download_file
        import socket
        
        # Mock timeout error
        mock_urlopen.side_effect = socket.timeout("Connection timed out")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "test.zip"
            
            with pytest.raises(RuntimeError, match="Failed to download file"):
                download_file("https://example.com/test.zip", temp_path)
    
    @patch('src.data_upload.boto3.client')
    def test_upload_to_s3_network_error_during_upload(self, mock_boto_client):
        """Test error handling for network issues during S3 upload"""
        from botocore.exceptions import ClientError
        from src.data_upload import upload_to_s3
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock successful bucket check
        mock_s3.head_bucket.return_value = {}
        
        # Mock network error during upload
        error_response = {'Error': {'Code': 'RequestTimeout', 'Message': 'Request timeout'}}
        mock_s3.upload_file.side_effect = ClientError(error_response, 'PutObject')
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = "test.csv"
            (temp_path / test_file).write_text("test data")
            
            with pytest.raises(ClientError):
                upload_to_s3(temp_path, "test-bucket", "raw-data/", [test_file])
    
    @patch('src.data_upload.boto3.client')
    def test_upload_to_s3_skips_missing_files(self, mock_boto_client):
        """Test that upload skips files that don't exist locally"""
        from src.data_upload import upload_to_s3
        
        # Mock S3 client
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3
        
        # Mock successful bucket check
        mock_s3.head_bucket.return_value = {}
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create only one file
            existing_file = "movies.csv"
            (temp_path / existing_file).write_text("test data")
            
            # Mock head_object
            mock_s3.head_object.return_value = {'ContentLength': len("test data")}
            
            # Try to upload multiple files (some don't exist)
            files_to_upload = ["movies.csv", "ratings.csv", "tags.csv"]
            upload_to_s3(temp_path, "test-bucket", "raw-data/", files_to_upload)
            
            # Verify only existing file was uploaded
            assert mock_s3.upload_file.call_count == 1
            call_args = mock_s3.upload_file.call_args
            assert existing_file in call_args[0][0]
