"""
Unit tests for retraining utilities.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock
from src.retraining import (
    get_latest_data_path,
    get_latest_dataset_directory,
    list_data_files_by_timestamp
)


# Helper functions for job name generation (from orchestration properties)
def generate_job_name_with_timestamp(prefix: str = "movielens-job") -> str:
    """Generate a unique job name using timestamp."""
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    return f"{prefix}-{timestamp}"


def generate_job_name_with_uuid(prefix: str = "movielens-job") -> str:
    """Generate a unique job name using UUID."""
    unique_id = str(uuid.uuid4())
    return f"{prefix}-{unique_id}"


def parse_cron_schedule(cron_expression: str) -> dict:
    """
    Parse a cron schedule expression and extract its components.
    
    Args:
        cron_expression: Cron expression (e.g., "0 2 ? * SUN *")
        
    Returns:
        Dictionary with parsed components: minute, hour, day_of_month, month, day_of_week, year
        
    Raises:
        ValueError: If cron expression is invalid
    """
    if not cron_expression or not isinstance(cron_expression, str):
        raise ValueError("Cron expression must be a non-empty string")
    
    parts = cron_expression.strip().split()
    
    if len(parts) != 6:
        raise ValueError(f"Cron expression must have 6 fields, got {len(parts)}")
    
    return {
        'minute': parts[0],
        'hour': parts[1],
        'day_of_month': parts[2],
        'month': parts[3],
        'day_of_week': parts[4],
        'year': parts[5]
    }


def validate_cron_schedule(cron_expression: str) -> bool:
    """
    Validate a cron schedule expression.
    
    Args:
        cron_expression: Cron expression to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        parsed = parse_cron_schedule(cron_expression)
        
        # Basic validation rules
        # Minute: 0-59 or *
        if parsed['minute'] not in ['*', '?'] and not (parsed['minute'].isdigit() and 0 <= int(parsed['minute']) <= 59):
            return False
        
        # Hour: 0-23 or *
        if parsed['hour'] not in ['*', '?'] and not (parsed['hour'].isdigit() and 0 <= int(parsed['hour']) <= 23):
            return False
        
        # Day of month: 1-31, ?, or *
        if parsed['day_of_month'] not in ['*', '?']:
            if not parsed['day_of_month'].isdigit():
                return False
            day = int(parsed['day_of_month'])
            if not (1 <= day <= 31):
                return False
        
        # Month: 1-12, *, or month names
        if parsed['month'] not in ['*', '?']:
            if not parsed['month'].isdigit():
                # Check if it's a valid month name
                valid_months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                               'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
                if parsed['month'].upper() not in valid_months:
                    return False
            else:
                month = int(parsed['month'])
                if not (1 <= month <= 12):
                    return False
        
        # Day of week: 1-7, *, ?, or day names
        if parsed['day_of_week'] not in ['*', '?']:
            if not parsed['day_of_week'].isdigit():
                # Check if it's a valid day name
                valid_days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
                if parsed['day_of_week'].upper() not in valid_days:
                    return False
            else:
                day = int(parsed['day_of_week'])
                if not (1 <= day <= 7):
                    return False
        
        # Year: 1970-2199, *, or ?
        if parsed['year'] not in ['*', '?']:
            if not parsed['year'].isdigit():
                return False
            year = int(parsed['year'])
            if not (1970 <= year <= 2199):
                return False
        
        return True
    except (ValueError, AttributeError):
        return False


class TestGetLatestDataPath:
    """Test get_latest_data_path function"""
    
    def test_returns_most_recent_file(self):
        """Test that the function returns the most recent file by timestamp"""
        # Create mock S3 client
        mock_s3 = Mock()
        
        # Mock response with multiple files at different timestamps
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed-data/2024-01-10/train.csv',
                    'LastModified': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed-data/2024-01-15/train.csv',
                    'LastModified': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed-data/2024-01-12/train.csv',
                    'LastModified': datetime(2024, 1, 12, 12, 0, 0, tzinfo=timezone.utc)
                }
            ]
        }
        
        result = get_latest_data_path('test-bucket', 'processed-data/', mock_s3)
        
        # Should return the file from 2024-01-15 (most recent)
        assert result == 's3://test-bucket/processed-data/2024-01-15/train.csv'
        mock_s3.list_objects_v2.assert_called_once_with(
            Bucket='test-bucket',
            Prefix='processed-data/'
        )
    
    def test_single_file(self):
        """Test with only one file in S3"""
        mock_s3 = Mock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed-data/train.csv',
                    'LastModified': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
                }
            ]
        }
        
        result = get_latest_data_path('test-bucket', 'processed-data/', mock_s3)
        assert result == 's3://test-bucket/processed-data/train.csv'
    
    def test_raises_error_when_no_files(self):
        """Test that ValueError is raised when no files are found"""
        mock_s3 = Mock()
        mock_s3.list_objects_v2.return_value = {}
        
        with pytest.raises(ValueError, match="No data files found"):
            get_latest_data_path('test-bucket', 'processed-data/', mock_s3)
    
    def test_raises_error_when_empty_contents(self):
        """Test that ValueError is raised when Contents is empty"""
        mock_s3 = Mock()
        mock_s3.list_objects_v2.return_value = {'Contents': []}
        
        with pytest.raises(ValueError, match="No data files found"):
            get_latest_data_path('test-bucket', 'processed-data/', mock_s3)
    
    def test_handles_s3_api_error(self):
        """Test error handling when S3 API call fails"""
        mock_s3 = Mock()
        mock_s3.list_objects_v2.side_effect = Exception("S3 API Error")
        
        with pytest.raises(ValueError, match="Failed to list objects"):
            get_latest_data_path('test-bucket', 'processed-data/', mock_s3)
    
    def test_uses_default_prefix(self):
        """Test that default prefix is used when not specified"""
        mock_s3 = Mock()
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed-data/train.csv',
                    'LastModified': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
                }
            ]
        }
        
        result = get_latest_data_path('test-bucket', s3_client=mock_s3)
        
        mock_s3.list_objects_v2.assert_called_once_with(
            Bucket='test-bucket',
            Prefix='processed-data/'
        )


class TestGetLatestDatasetDirectory:
    """Test get_latest_dataset_directory function"""
    
    def test_returns_most_recent_directory(self):
        """Test that the function returns the most recent directory"""
        mock_s3 = Mock()
        
        # Mock response for directory listing
        mock_s3.list_objects_v2.side_effect = [
            # First call: list directories
            {
                'CommonPrefixes': [
                    {'Prefix': 'processed-data/2024-01-10/'},
                    {'Prefix': 'processed-data/2024-01-15/'},
                    {'Prefix': 'processed-data/2024-01-12/'}
                ]
            },
            # Subsequent calls: get timestamps for each directory
            {
                'Contents': [
                    {'LastModified': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)}
                ]
            },
            {
                'Contents': [
                    {'LastModified': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)}
                ]
            },
            {
                'Contents': [
                    {'LastModified': datetime(2024, 1, 12, 12, 0, 0, tzinfo=timezone.utc)}
                ]
            }
        ]
        
        result = get_latest_dataset_directory('test-bucket', 'processed-data/', mock_s3)
        
        # Should return the directory from 2024-01-15 (most recent)
        assert result == 's3://test-bucket/processed-data/2024-01-15/'
    
    def test_raises_error_when_no_directories(self):
        """Test that ValueError is raised when no directories are found"""
        mock_s3 = Mock()
        mock_s3.list_objects_v2.return_value = {}
        
        with pytest.raises(ValueError, match="No directories found"):
            get_latest_dataset_directory('test-bucket', 'processed-data/', mock_s3)
    
    def test_handles_inaccessible_directories(self):
        """Test that inaccessible directories are skipped"""
        mock_s3 = Mock()
        
        mock_s3.list_objects_v2.side_effect = [
            # First call: list directories
            {
                'CommonPrefixes': [
                    {'Prefix': 'processed-data/2024-01-10/'},
                    {'Prefix': 'processed-data/2024-01-15/'}
                ]
            },
            # Second call: first directory fails
            Exception("Access denied"),
            # Third call: second directory succeeds
            {
                'Contents': [
                    {'LastModified': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)}
                ]
            }
        ]
        
        result = get_latest_dataset_directory('test-bucket', 'processed-data/', mock_s3)
        assert result == 's3://test-bucket/processed-data/2024-01-15/'


class TestListDataFilesByTimestamp:
    """Test list_data_files_by_timestamp function"""
    
    def test_returns_sorted_file_list(self):
        """Test that files are returned sorted by timestamp (most recent first)"""
        mock_s3 = Mock()
        
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed-data/2024-01-10/train.csv',
                    'LastModified': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
                    'Size': 1024
                },
                {
                    'Key': 'processed-data/2024-01-15/train.csv',
                    'LastModified': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'Size': 2048
                },
                {
                    'Key': 'processed-data/2024-01-12/train.csv',
                    'LastModified': datetime(2024, 1, 12, 12, 0, 0, tzinfo=timezone.utc),
                    'Size': 1536
                }
            ]
        }
        
        result = list_data_files_by_timestamp('test-bucket', 'processed-data/', mock_s3)
        
        # Should be sorted by timestamp (most recent first)
        assert len(result) == 3
        assert result[0]['key'] == 'processed-data/2024-01-15/train.csv'
        assert result[0]['uri'] == 's3://test-bucket/processed-data/2024-01-15/train.csv'
        assert result[0]['size'] == 2048
        assert result[1]['key'] == 'processed-data/2024-01-12/train.csv'
        assert result[2]['key'] == 'processed-data/2024-01-10/train.csv'
    
    def test_raises_error_when_no_files(self):
        """Test that ValueError is raised when no files are found"""
        mock_s3 = Mock()
        mock_s3.list_objects_v2.return_value = {}
        
        with pytest.raises(ValueError, match="No files found"):
            list_data_files_by_timestamp('test-bucket', 'processed-data/', mock_s3)
    
    def test_includes_all_file_metadata(self):
        """Test that all file metadata is included in results"""
        mock_s3 = Mock()
        
        timestamp = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed-data/train.csv',
                    'LastModified': timestamp,
                    'Size': 1024
                }
            ]
        }
        
        result = list_data_files_by_timestamp('test-bucket', 'processed-data/', mock_s3)
        
        assert len(result) == 1
        assert result[0]['key'] == 'processed-data/train.csv'
        assert result[0]['uri'] == 's3://test-bucket/processed-data/train.csv'
        assert result[0]['last_modified'] == timestamp
        assert result[0]['size'] == 1024



class TestCronScheduleParsing:
    """Test cron schedule parsing for EventBridge rules"""
    
    def test_parse_valid_weekly_schedule(self):
        """Test parsing the weekly retraining schedule (Sunday at 2 AM UTC)"""
        # Requirements 11.1, 11.2: Every Sunday at 2 AM UTC
        cron_expression = "0 2 ? * SUN *"
        
        result = parse_cron_schedule(cron_expression)
        
        assert result['minute'] == '0'
        assert result['hour'] == '2'
        assert result['day_of_month'] == '?'
        assert result['month'] == '*'
        assert result['day_of_week'] == 'SUN'
        assert result['year'] == '*'
    
    def test_parse_daily_schedule(self):
        """Test parsing a daily schedule"""
        cron_expression = "0 3 * * ? *"
        
        result = parse_cron_schedule(cron_expression)
        
        assert result['minute'] == '0'
        assert result['hour'] == '3'
        assert result['day_of_month'] == '*'
        assert result['month'] == '*'
        assert result['day_of_week'] == '?'
        assert result['year'] == '*'
    
    def test_parse_monthly_schedule(self):
        """Test parsing a monthly schedule (first day of month)"""
        cron_expression = "0 0 1 * ? *"
        
        result = parse_cron_schedule(cron_expression)
        
        assert result['minute'] == '0'
        assert result['hour'] == '0'
        assert result['day_of_month'] == '1'
        assert result['month'] == '*'
        assert result['day_of_week'] == '?'
        assert result['year'] == '*'
    
    def test_parse_specific_date_schedule(self):
        """Test parsing a schedule for a specific date"""
        cron_expression = "30 14 15 6 ? 2024"
        
        result = parse_cron_schedule(cron_expression)
        
        assert result['minute'] == '30'
        assert result['hour'] == '14'
        assert result['day_of_month'] == '15'
        assert result['month'] == '6'
        assert result['day_of_week'] == '?'
        assert result['year'] == '2024'
    
    def test_parse_invalid_expression_too_few_fields(self):
        """Test that parsing fails with too few fields"""
        cron_expression = "0 2 ? *"
        
        with pytest.raises(ValueError, match="must have 6 fields"):
            parse_cron_schedule(cron_expression)
    
    def test_parse_invalid_expression_too_many_fields(self):
        """Test that parsing fails with too many fields"""
        cron_expression = "0 2 ? * SUN * extra"
        
        with pytest.raises(ValueError, match="must have 6 fields"):
            parse_cron_schedule(cron_expression)
    
    def test_parse_empty_expression(self):
        """Test that parsing fails with empty expression"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            parse_cron_schedule("")
    
    def test_parse_none_expression(self):
        """Test that parsing fails with None"""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            parse_cron_schedule(None)
    
    def test_validate_weekly_schedule(self):
        """Test validation of the weekly retraining schedule"""
        cron_expression = "0 2 ? * SUN *"
        
        assert validate_cron_schedule(cron_expression) is True
    
    def test_validate_invalid_minute(self):
        """Test validation fails with invalid minute (> 59)"""
        cron_expression = "60 2 ? * SUN *"
        
        assert validate_cron_schedule(cron_expression) is False
    
    def test_validate_invalid_hour(self):
        """Test validation fails with invalid hour (> 23)"""
        cron_expression = "0 24 ? * SUN *"
        
        assert validate_cron_schedule(cron_expression) is False
    
    def test_validate_invalid_day_of_month(self):
        """Test validation fails with invalid day of month (> 31)"""
        cron_expression = "0 2 32 * ? *"
        
        assert validate_cron_schedule(cron_expression) is False
    
    def test_validate_invalid_month(self):
        """Test validation fails with invalid month (> 12)"""
        cron_expression = "0 2 1 13 ? *"
        
        assert validate_cron_schedule(cron_expression) is False
    
    def test_validate_invalid_day_of_week(self):
        """Test validation fails with invalid day of week (> 7)"""
        cron_expression = "0 2 ? * 8 *"
        
        assert validate_cron_schedule(cron_expression) is False
    
    def test_validate_invalid_year(self):
        """Test validation fails with invalid year (< 1970)"""
        cron_expression = "0 2 ? * SUN 1969"
        
        assert validate_cron_schedule(cron_expression) is False
    
    def test_validate_with_month_names(self):
        """Test validation with month names"""
        cron_expression = "0 2 1 JAN ? *"
        
        assert validate_cron_schedule(cron_expression) is True
    
    def test_validate_with_day_names(self):
        """Test validation with day names"""
        cron_expression = "0 2 ? * MON *"
        
        assert validate_cron_schedule(cron_expression) is True
    
    def test_validate_all_wildcards(self):
        """Test validation with all wildcards"""
        cron_expression = "* * * * * *"
        
        assert validate_cron_schedule(cron_expression) is True


class TestJobNameGeneration:
    """Test job name generation for Step Functions executions"""
    
    def test_generate_job_name_with_timestamp(self):
        """Test job name generation with timestamp"""
        # Requirement 11.3: Generate unique job names
        prefix = "movielens-training"
        
        job_name = generate_job_name_with_timestamp(prefix)
        
        # Should start with prefix
        assert job_name.startswith(prefix)
        
        # Should contain timestamp
        assert len(job_name) > len(prefix)
        
        # Should contain hyphens separating components
        assert '-' in job_name
        
        # Should be a valid string
        assert isinstance(job_name, str)
        assert len(job_name) > 0
    
    def test_generate_job_name_with_uuid(self):
        """Test job name generation with UUID"""
        prefix = "movielens-training"
        
        job_name = generate_job_name_with_uuid(prefix)
        
        # Should start with prefix
        assert job_name.startswith(prefix)
        
        # Should contain UUID
        assert len(job_name) > len(prefix)
        
        # Should contain hyphens (UUID format)
        assert job_name.count('-') >= 5  # UUID has 4 hyphens + 1 for prefix separator
        
        # Should be a valid string
        assert isinstance(job_name, str)
        assert len(job_name) > 0
    
    def test_job_name_uniqueness_timestamp(self):
        """Test that timestamp-based job names are unique"""
        prefix = "test-job"
        
        # Generate multiple job names
        job_names = []
        for _ in range(10):
            job_name = generate_job_name_with_timestamp(prefix)
            job_names.append(job_name)
            # Small delay to ensure timestamp changes
            import time
            time.sleep(0.001)
        
        # All should be unique
        assert len(set(job_names)) == len(job_names)
    
    def test_job_name_uniqueness_uuid(self):
        """Test that UUID-based job names are unique"""
        prefix = "test-job"
        
        # Generate multiple job names
        job_names = [generate_job_name_with_uuid(prefix) for _ in range(100)]
        
        # All should be unique
        assert len(set(job_names)) == len(job_names)
    
    def test_job_name_with_default_prefix(self):
        """Test job name generation with default prefix"""
        job_name = generate_job_name_with_timestamp()
        
        # Should use default prefix
        assert job_name.startswith("movielens-job")
    
    def test_job_name_with_custom_prefix(self):
        """Test job name generation with custom prefix"""
        custom_prefix = "my-custom-prefix"
        
        job_name = generate_job_name_with_timestamp(custom_prefix)
        
        # Should use custom prefix
        assert job_name.startswith(custom_prefix)
    
    def test_job_name_format_timestamp(self):
        """Test that timestamp-based job names follow expected format"""
        prefix = "test"
        
        job_name = generate_job_name_with_timestamp(prefix)
        
        # Should have format: prefix-YYYYMMDD-HHMMSS-microseconds
        parts = job_name.split('-')
        assert len(parts) >= 4  # prefix, date, time, microseconds
        
        # Date part should be 8 digits (YYYYMMDD)
        date_part = parts[1]
        assert len(date_part) == 8
        assert date_part.isdigit()
        
        # Time part should be 6 digits (HHMMSS)
        time_part = parts[2]
        assert len(time_part) == 6
        assert time_part.isdigit()
        
        # Microseconds part should be digits
        microseconds_part = parts[3]
        assert microseconds_part.isdigit()
    
    def test_job_name_format_uuid(self):
        """Test that UUID-based job names follow expected format"""
        prefix = "test"
        
        job_name = generate_job_name_with_uuid(prefix)
        
        # Should have format: prefix-UUID
        parts = job_name.split('-', 1)  # Split only on first hyphen
        assert len(parts) == 2
        assert parts[0] == prefix
        
        # UUID part should be valid UUID format
        uuid_part = parts[1]
        import re
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, uuid_part), f"UUID part should match pattern: {uuid_part}"
    
    def test_job_name_aws_compatible(self):
        """Test that job names are compatible with AWS naming requirements"""
        prefix = "movielens-job"
        
        job_name = generate_job_name_with_timestamp(prefix)
        
        # AWS job names typically have length limits
        assert len(job_name) <= 256
        assert len(job_name) >= 3
        
        # Should only contain alphanumeric, hyphens, and underscores
        import re
        assert re.match(r'^[a-zA-Z0-9\-_]+$', job_name), \
            f"Job name should only contain alphanumeric, hyphens, and underscores: {job_name}"
    
    def test_job_name_no_spaces(self):
        """Test that job names don't contain spaces"""
        prefix = "test-job"
        
        job_name_timestamp = generate_job_name_with_timestamp(prefix)
        job_name_uuid = generate_job_name_with_uuid(prefix)
        
        assert ' ' not in job_name_timestamp
        assert ' ' not in job_name_uuid
    
    def test_job_name_sortable(self):
        """Test that timestamp-based job names are sortable chronologically"""
        prefix = "test"
        
        # Generate job names with delays
        job_names = []
        for _ in range(5):
            job_name = generate_job_name_with_timestamp(prefix)
            job_names.append(job_name)
            import time
            time.sleep(0.01)  # 10ms delay
        
        # Sorted names should be in chronological order
        sorted_names = sorted(job_names)
        assert sorted_names == job_names, \
            "Timestamp-based job names should be sortable chronologically"


class TestDataSelectionWithMultipleFiles:
    """Test data selection logic with multiple files (Requirement 11.4)"""
    
    def test_select_latest_from_multiple_files(self):
        """Test selecting the latest file from multiple options"""
        mock_s3 = Mock()
        
        # Create multiple files with different timestamps
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed-data/2024-01-10/train.csv',
                    'LastModified': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed-data/2024-01-15/train.csv',
                    'LastModified': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed-data/2024-01-12/train.csv',
                    'LastModified': datetime(2024, 1, 12, 12, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed-data/2024-01-08/train.csv',
                    'LastModified': datetime(2024, 1, 8, 12, 0, 0, tzinfo=timezone.utc)
                }
            ]
        }
        
        result = get_latest_data_path('test-bucket', 'processed-data/', mock_s3)
        
        # Should select the file from 2024-01-15 (most recent)
        assert result == 's3://test-bucket/processed-data/2024-01-15/train.csv'
    
    def test_select_latest_with_same_day_different_times(self):
        """Test selecting latest file when multiple files exist on same day"""
        mock_s3 = Mock()
        
        # Multiple files on same day but different times
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed-data/morning.csv',
                    'LastModified': datetime(2024, 1, 15, 8, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed-data/afternoon.csv',
                    'LastModified': datetime(2024, 1, 15, 14, 0, 0, tzinfo=timezone.utc)
                },
                {
                    'Key': 'processed-data/evening.csv',
                    'LastModified': datetime(2024, 1, 15, 20, 0, 0, tzinfo=timezone.utc)
                }
            ]
        }
        
        result = get_latest_data_path('test-bucket', 'processed-data/', mock_s3)
        
        # Should select the evening file (most recent time)
        assert result == 's3://test-bucket/processed-data/evening.csv'
    
    def test_select_latest_with_many_files(self):
        """Test selecting latest from a large number of files"""
        mock_s3 = Mock()
        
        # Generate many files
        base_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        files = []
        
        for i in range(50):
            from datetime import timedelta
            timestamp = base_date + timedelta(days=i)
            files.append({
                'Key': f'processed-data/day-{i}/train.csv',
                'LastModified': timestamp
            })
        
        mock_s3.list_objects_v2.return_value = {'Contents': files}
        
        result = get_latest_data_path('test-bucket', 'processed-data/', mock_s3)
        
        # Should select the last file (day 49)
        assert result == 's3://test-bucket/processed-data/day-49/train.csv'
    
    def test_list_files_sorted_by_timestamp(self):
        """Test that list_data_files_by_timestamp returns files in correct order"""
        mock_s3 = Mock()
        
        mock_s3.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'processed-data/2024-01-10/train.csv',
                    'LastModified': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc),
                    'Size': 1024
                },
                {
                    'Key': 'processed-data/2024-01-15/train.csv',
                    'LastModified': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
                    'Size': 2048
                },
                {
                    'Key': 'processed-data/2024-01-12/train.csv',
                    'LastModified': datetime(2024, 1, 12, 12, 0, 0, tzinfo=timezone.utc),
                    'Size': 1536
                }
            ]
        }
        
        result = list_data_files_by_timestamp('test-bucket', 'processed-data/', mock_s3)
        
        # Should be sorted by timestamp (most recent first)
        assert len(result) == 3
        assert result[0]['key'] == 'processed-data/2024-01-15/train.csv'
        assert result[1]['key'] == 'processed-data/2024-01-12/train.csv'
        assert result[2]['key'] == 'processed-data/2024-01-10/train.csv'
        
        # Verify timestamps are in descending order
        for i in range(len(result) - 1):
            assert result[i]['last_modified'] >= result[i + 1]['last_modified']
    
    def test_select_latest_directory_from_multiple(self):
        """Test selecting latest directory from multiple dated directories"""
        mock_s3 = Mock()
        
        # Mock directory listing and timestamp queries
        mock_s3.list_objects_v2.side_effect = [
            # First call: list directories
            {
                'CommonPrefixes': [
                    {'Prefix': 'processed-data/2024-01-10/'},
                    {'Prefix': 'processed-data/2024-01-15/'},
                    {'Prefix': 'processed-data/2024-01-12/'},
                    {'Prefix': 'processed-data/2024-01-08/'}
                ]
            },
            # Subsequent calls: get timestamps for each directory
            {'Contents': [{'LastModified': datetime(2024, 1, 10, 12, 0, 0, tzinfo=timezone.utc)}]},
            {'Contents': [{'LastModified': datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)}]},
            {'Contents': [{'LastModified': datetime(2024, 1, 12, 12, 0, 0, tzinfo=timezone.utc)}]},
            {'Contents': [{'LastModified': datetime(2024, 1, 8, 12, 0, 0, tzinfo=timezone.utc)}]}
        ]
        
        result = get_latest_dataset_directory('test-bucket', 'processed-data/', mock_s3)
        
        # Should select the directory from 2024-01-15 (most recent)
        assert result == 's3://test-bucket/processed-data/2024-01-15/'
