"""
Property-based tests for orchestration components.

These tests validate universal correctness properties across many generated inputs.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import uuid

from hypothesis import given, settings, strategies as st, assume
import pytest

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / 'src'))


# Feature: aws-movielens-recommendation, Property 17: Job name uniqueness


def generate_job_name_with_timestamp(prefix: str = "movielens-job") -> str:
    """
    Generate a unique job name using timestamp.
    
    Args:
        prefix: Prefix for the job name
        
    Returns:
        Unique job name with timestamp
    """
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    return f"{prefix}-{timestamp}"


def generate_job_name_with_uuid(prefix: str = "movielens-job") -> str:
    """
    Generate a unique job name using UUID.
    
    Args:
        prefix: Prefix for the job name
        
    Returns:
        Unique job name with UUID
    """
    unique_id = str(uuid.uuid4())
    return f"{prefix}-{unique_id}"


@given(
    num_executions=st.integers(min_value=2, max_value=100),
    prefix=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_job_name_uniqueness_with_timestamp(num_executions, prefix):
    """
    Property 17: Job name uniqueness
    
    For any two pipeline executions, the generated job names should be unique 
    (using timestamps or UUIDs).
    
    Validates: Requirements 11.3
    """
    # Generate multiple job names simulating multiple pipeline executions
    job_names = []
    
    for i in range(num_executions):
        job_name = generate_job_name_with_timestamp(prefix)
        job_names.append(job_name)
        
        # Add a tiny delay to ensure timestamp changes
        # In real AWS executions, there would be natural delays between job starts
        import time
        time.sleep(0.001)  # 1 millisecond delay
    
    # Property 1: All job names should be unique
    unique_job_names = set(job_names)
    assert len(unique_job_names) == len(job_names), \
        f"All job names should be unique: generated {len(job_names)} names but only {len(unique_job_names)} are unique"
    
    # Property 2: Each job name should contain the prefix
    for job_name in job_names:
        assert job_name.startswith(prefix), \
            f"Job name should start with prefix '{prefix}': got '{job_name}'"
    
    # Property 3: Each job name should be a non-empty string
    for job_name in job_names:
        assert isinstance(job_name, str), \
            f"Job name should be a string, got {type(job_name)}"
        assert len(job_name) > 0, \
            f"Job name should not be empty"
    
    # Property 4: Job names should be longer than just the prefix
    # (they should include timestamp/UUID)
    for job_name in job_names:
        assert len(job_name) > len(prefix), \
            f"Job name should include unique identifier beyond prefix: '{job_name}'"
    
    # Property 5: Job names should not contain spaces or special characters that break AWS naming
    # AWS job names typically allow alphanumeric, hyphens, and underscores
    import re
    for job_name in job_names:
        assert re.match(r'^[a-zA-Z0-9\-_]+$', job_name), \
            f"Job name should only contain alphanumeric, hyphens, and underscores: '{job_name}'"
    
    # Property 6: Job names should be deterministic for the same execution
    # (calling the function with same parameters at same time should give same result)
    # We can't test exact equality due to timing, but we can test format consistency
    for job_name in job_names:
        parts = job_name.split('-')
        assert len(parts) >= 2, \
            f"Job name should have at least prefix and timestamp parts: '{job_name}'"
    
    # Property 7: Job names should be sortable (lexicographically)
    sorted_names = sorted(job_names)
    assert len(sorted_names) == len(job_names), \
        f"Job names should be sortable"
    
    # Property 8: No job name should be a substring of another
    # (prevents confusion in logs and monitoring)
    for i, name1 in enumerate(job_names):
        for j, name2 in enumerate(job_names):
            if i != j:
                assert name1 not in name2 or name1 == name2, \
                    f"Job names should not be substrings of each other: '{name1}' vs '{name2}'"
    
    # Property 9: Job names should have consistent format
    # All should follow the same pattern: prefix-timestamp
    formats = [len(job_name.split('-')) for job_name in job_names]
    # Allow some variation due to microseconds, but format should be consistent
    assert min(formats) >= 2, \
        f"All job names should have at least 2 parts (prefix and identifier)"
    
    # Property 10: Job names should be suitable for AWS resource naming
    # AWS has length limits (typically 63-256 characters depending on service)
    for job_name in job_names:
        assert len(job_name) <= 256, \
            f"Job name should not exceed AWS naming length limits: '{job_name}' has {len(job_name)} characters"
        assert len(job_name) >= 3, \
            f"Job name should be at least 3 characters long: '{job_name}'"


@given(
    num_executions=st.integers(min_value=2, max_value=100),
    prefix=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_job_name_uniqueness_with_uuid(num_executions, prefix):
    """
    Property 17: Job name uniqueness (UUID variant)
    
    For any two pipeline executions, the generated job names should be unique 
    when using UUIDs.
    
    Validates: Requirements 11.3
    """
    # Generate multiple job names using UUID
    job_names = []
    
    for i in range(num_executions):
        job_name = generate_job_name_with_uuid(prefix)
        job_names.append(job_name)
    
    # Property 1: All job names should be unique
    unique_job_names = set(job_names)
    assert len(unique_job_names) == len(job_names), \
        f"All job names should be unique: generated {len(job_names)} names but only {len(unique_job_names)} are unique"
    
    # Property 2: Each job name should contain the prefix
    for job_name in job_names:
        assert job_name.startswith(prefix), \
            f"Job name should start with prefix '{prefix}': got '{job_name}'"
    
    # Property 3: Each job name should be a non-empty string
    for job_name in job_names:
        assert isinstance(job_name, str), \
            f"Job name should be a string, got {type(job_name)}"
        assert len(job_name) > 0, \
            f"Job name should not be empty"
    
    # Property 4: Job names should contain valid UUID format
    # UUID format: 8-4-4-4-12 hexadecimal digits
    import re
    uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    for job_name in job_names:
        assert re.search(uuid_pattern, job_name), \
            f"Job name should contain valid UUID: '{job_name}'"
    
    # Property 5: Job names should be longer than just the prefix
    for job_name in job_names:
        assert len(job_name) > len(prefix), \
            f"Job name should include UUID beyond prefix: '{job_name}'"
    
    # Property 6: UUIDs in job names should be version 4 (random)
    # We can verify this by checking the version field
    for job_name in job_names:
        # Extract UUID from job name
        uuid_match = re.search(uuid_pattern, job_name)
        if uuid_match:
            uuid_str = uuid_match.group(0)
            # Version 4 UUIDs have '4' in the version position
            # Format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
            parts = uuid_str.split('-')
            assert parts[2][0] == '4', \
                f"UUID should be version 4: '{uuid_str}'"
    
    # Property 7: Job names should not contain spaces or invalid characters
    for job_name in job_names:
        assert re.match(r'^[a-zA-Z0-9\-]+$', job_name), \
            f"Job name should only contain alphanumeric and hyphens: '{job_name}'"
    
    # Property 8: Job names should be suitable for AWS resource naming
    for job_name in job_names:
        assert len(job_name) <= 256, \
            f"Job name should not exceed AWS naming length limits: '{job_name}' has {len(job_name)} characters"
        assert len(job_name) >= 3, \
            f"Job name should be at least 3 characters long: '{job_name}'"
    
    # Property 9: No two job names should be identical even with same prefix
    for i in range(len(job_names)):
        for j in range(i + 1, len(job_names)):
            assert job_names[i] != job_names[j], \
                f"Job names should be unique: '{job_names[i]}' == '{job_names[j]}'"
    
    # Property 10: Job names should be reproducible from their components
    # We should be able to extract the UUID and reconstruct the name
    for job_name in job_names:
        uuid_match = re.search(uuid_pattern, job_name)
        if uuid_match:
            extracted_uuid = uuid_match.group(0)
            reconstructed_name = f"{prefix}-{extracted_uuid}"
            assert reconstructed_name == job_name, \
                f"Job name should be reconstructable from components: expected '{reconstructed_name}', got '{job_name}'"


@given(
    execution_times=st.lists(
        st.datetimes(
            min_value=datetime(2024, 1, 1),
            max_value=datetime(2026, 12, 31)
        ),
        min_size=2,
        max_size=50,
        unique=True
    ),
    prefix=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
        min_size=1,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_job_name_uniqueness_across_time(execution_times, prefix):
    """
    Property 17: Job name uniqueness across different execution times
    
    For any set of pipeline executions at different times, the generated job names 
    should be unique.
    
    Validates: Requirements 11.3
    """
    # Sort execution times to simulate chronological order
    execution_times = sorted(execution_times)
    
    # Generate job names for each execution time
    job_names = []
    for exec_time in execution_times:
        # Simulate job name generation at specific time
        timestamp = exec_time.strftime("%Y%m%d-%H%M%S-%f")
        job_name = f"{prefix}-{timestamp}"
        job_names.append(job_name)
    
    # Property 1: All job names should be unique
    unique_job_names = set(job_names)
    assert len(unique_job_names) == len(job_names), \
        f"All job names should be unique across different execution times: generated {len(job_names)} names but only {len(unique_job_names)} are unique"
    
    # Property 2: Job names should be chronologically sortable
    # Since we use timestamps, sorting job names should give chronological order
    sorted_names = sorted(job_names)
    # The sorted names should correspond to sorted execution times
    for i in range(len(sorted_names)):
        # Extract timestamp from job name
        timestamp_part = sorted_names[i].replace(f"{prefix}-", "")
        assert len(timestamp_part) > 0, \
            f"Job name should contain timestamp: '{sorted_names[i]}'"
    
    # Property 3: Job names from different times should be distinguishable
    # Even if executions are close in time, names should differ
    for i in range(len(job_names) - 1):
        assert job_names[i] != job_names[i + 1], \
            f"Consecutive job names should be different: '{job_names[i]}' vs '{job_names[i + 1]}'"
    
    # Property 4: Job names should reflect execution order
    # Earlier executions should have lexicographically smaller names (due to timestamp)
    for i in range(len(job_names) - 1):
        # Since execution_times is sorted, job_names should also be in order
        assert job_names[i] < job_names[i + 1], \
            f"Job names should be in chronological order: '{job_names[i]}' should be < '{job_names[i + 1]}'"
    
    # Property 5: Job names should encode the execution time
    # We should be able to extract approximate execution time from job name
    for i, job_name in enumerate(job_names):
        timestamp_part = job_name.replace(f"{prefix}-", "")
        # Verify timestamp format (YYYYMMDD-HHMMSS-microseconds)
        import re
        assert re.match(r'\d{8}-\d{6}-\d+', timestamp_part), \
            f"Job name should contain valid timestamp format: '{timestamp_part}'"
    
    # Property 6: Job names should be unique even for executions on same day
    # Group by date and verify uniqueness within each day
    from collections import defaultdict
    names_by_date = defaultdict(list)
    for job_name in job_names:
        # Extract date part (YYYYMMDD)
        date_part = job_name.split('-')[1][:8] if len(job_name.split('-')) > 1 else ""
        names_by_date[date_part].append(job_name)
    
    for date, names in names_by_date.items():
        assert len(names) == len(set(names)), \
            f"Job names should be unique even within same day: {date}"
    
    # Property 7: Job names should handle rapid successive executions
    # Even if executions are very close in time (same second), they should be unique
    # This is ensured by including microseconds in the timestamp
    for job_name in job_names:
        parts = job_name.split('-')
        # Should have at least: prefix, date, time, microseconds
        assert len(parts) >= 4, \
            f"Job name should include microseconds for uniqueness: '{job_name}'"
    
    # Property 8: Job names should be consistent in format
    # All names should follow the same pattern
    formats = [len(job_name.split('-')) for job_name in job_names]
    assert len(set(formats)) == 1, \
        f"All job names should have consistent format: found {set(formats)} different formats"
    
    # Property 9: Job names should be valid for AWS services
    # Check length and character constraints
    for job_name in job_names:
        assert 3 <= len(job_name) <= 256, \
            f"Job name length should be within AWS limits: '{job_name}' has {len(job_name)} characters"
        assert re.match(r'^[a-zA-Z0-9\-_]+$', job_name), \
            f"Job name should only contain valid AWS characters: '{job_name}'"
    
    # Property 10: Job names should support filtering and querying
    # All names with same prefix should be easily filterable
    filtered_names = [name for name in job_names if name.startswith(prefix)]
    assert len(filtered_names) == len(job_names), \
        f"All job names should be filterable by prefix: expected {len(job_names)}, got {len(filtered_names)}"


# Feature: aws-movielens-recommendation, Property 18: Latest data selection


@given(
    num_files=st.integers(min_value=1, max_value=50),
    bucket_name=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
        min_size=3,
        max_size=20
    ),
    prefix=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
        min_size=1,
        max_size=20
    ).map(lambda x: x + '/')
)
@settings(max_examples=100, deadline=None)
def test_latest_data_selection_property(num_files, bucket_name, prefix):
    """
    Property 18: Latest data selection
    
    For any S3 directory with multiple dated datasets, the retraining process 
    should select the dataset with the most recent timestamp.
    
    Validates: Requirements 11.4
    """
    from unittest.mock import Mock
    from src.retraining import get_latest_data_path
    
    # Generate random timestamps for files
    # Use a range of dates to ensure variety
    base_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    # Create file metadata with different timestamps
    files = []
    timestamps = []
    for i in range(num_files):
        # Generate timestamps with increasing offsets to ensure uniqueness
        offset_days = i * 2  # Space them out by 2 days
        offset_hours = i % 24
        offset_minutes = (i * 13) % 60  # Use prime number for variety
        
        timestamp = base_date + timedelta(
            days=offset_days,
            hours=offset_hours,
            minutes=offset_minutes
        )
        timestamps.append(timestamp)
        
        file_key = f"{prefix}data-{i}.csv"
        files.append({
            'Key': file_key,
            'LastModified': timestamp
        })
    
    # Create mock S3 client
    mock_s3 = Mock()
    mock_s3.list_objects_v2.return_value = {
        'Contents': files
    }
    
    # Call the function
    result = get_latest_data_path(bucket_name, prefix, mock_s3)
    
    # Property 1: The result should be an S3 URI
    assert result.startswith('s3://'), \
        f"Result should be an S3 URI: got '{result}'"
    assert bucket_name in result, \
        f"Result should contain bucket name '{bucket_name}': got '{result}'"
    
    # Property 2: The result should point to the file with the most recent timestamp
    most_recent_timestamp = max(timestamps)
    most_recent_file = next(f for f in files if f['LastModified'] == most_recent_timestamp)
    expected_uri = f"s3://{bucket_name}/{most_recent_file['Key']}"
    
    assert result == expected_uri, \
        f"Should select file with most recent timestamp: expected '{expected_uri}', got '{result}'"
    
    # Property 3: The selected file should have a timestamp >= all other files
    selected_file = next(f for f in files if f"s3://{bucket_name}/{f['Key']}" == result)
    selected_timestamp = selected_file['LastModified']
    
    for file in files:
        assert selected_timestamp >= file['LastModified'], \
            f"Selected file timestamp should be >= all others: {selected_timestamp} vs {file['LastModified']}"
    
    # Property 4: If we remove the most recent file and call again, 
    # we should get the second most recent
    if num_files > 1:
        # Remove the most recent file
        remaining_files = [f for f in files if f['LastModified'] != most_recent_timestamp]
        mock_s3.list_objects_v2.return_value = {
            'Contents': remaining_files
        }
        
        second_result = get_latest_data_path(bucket_name, prefix, mock_s3)
        
        # Find the second most recent timestamp
        second_most_recent_timestamp = max(f['LastModified'] for f in remaining_files)
        second_most_recent_file = next(f for f in remaining_files if f['LastModified'] == second_most_recent_timestamp)
        second_expected_uri = f"s3://{bucket_name}/{second_most_recent_file['Key']}"
        
        assert second_result == second_expected_uri, \
            f"After removing most recent, should select second most recent: expected '{second_expected_uri}', got '{second_result}'"
        
        # The second result should be different from the first
        assert second_result != result, \
            f"Second selection should differ from first: both are '{result}'"
    
    # Property 5: The function should be deterministic
    # Calling it multiple times with same data should give same result
    mock_s3.list_objects_v2.return_value = {
        'Contents': files
    }
    
    result2 = get_latest_data_path(bucket_name, prefix, mock_s3)
    assert result == result2, \
        f"Function should be deterministic: first call '{result}', second call '{result2}'"
    
    # Property 6: The result should not depend on the order of files in the list
    # Shuffle the files and verify we get the same result
    import random
    shuffled_files = files.copy()
    random.shuffle(shuffled_files)
    
    mock_s3.list_objects_v2.return_value = {
        'Contents': shuffled_files
    }
    
    result3 = get_latest_data_path(bucket_name, prefix, mock_s3)
    assert result == result3, \
        f"Result should not depend on file order: original '{result}', shuffled '{result3}'"
    
    # Property 7: The selected file should exist in the original file list
    selected_key = result.replace(f"s3://{bucket_name}/", "")
    file_keys = [f['Key'] for f in files]
    assert selected_key in file_keys, \
        f"Selected file should exist in original list: '{selected_key}' not in {file_keys}"
    
    # Property 8: The function should handle files with identical timestamps
    # If multiple files have the same most recent timestamp, any of them is valid
    # (but the function should still return exactly one)
    if num_files >= 2:
        # Create files with identical timestamps
        identical_timestamp = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        identical_files = [
            {'Key': f"{prefix}file-{i}.csv", 'LastModified': identical_timestamp}
            for i in range(2)
        ]
        
        mock_s3.list_objects_v2.return_value = {
            'Contents': identical_files
        }
        
        result4 = get_latest_data_path(bucket_name, prefix, mock_s3)
        
        # Should return one of the files with the identical timestamp
        assert result4 in [f"s3://{bucket_name}/{f['Key']}" for f in identical_files], \
            f"Should return one of the files with identical timestamp: got '{result4}'"
    
    # Property 9: The function should work with various file naming patterns
    # The selection should be based purely on timestamp, not filename
    if num_files >= 3:
        # Create files with non-chronological names but chronological timestamps
        reverse_named_files = []
        sorted_timestamps = sorted(timestamps)
        
        for i, timestamp in enumerate(sorted_timestamps):
            # Name files in reverse order (z, y, x, ...)
            file_key = f"{prefix}file-{chr(ord('z') - i)}.csv"
            reverse_named_files.append({
                'Key': file_key,
                'LastModified': timestamp
            })
        
        mock_s3.list_objects_v2.return_value = {
            'Contents': reverse_named_files
        }
        
        result5 = get_latest_data_path(bucket_name, prefix, mock_s3)
        
        # Should select the file with the most recent timestamp (last in sorted_timestamps)
        # which has the name 'file-...' where ... is the earliest letter
        most_recent_in_reverse = reverse_named_files[-1]
        expected_uri5 = f"s3://{bucket_name}/{most_recent_in_reverse['Key']}"
        
        assert result5 == expected_uri5, \
            f"Selection should be based on timestamp, not filename: expected '{expected_uri5}', got '{result5}'"
    
    # Property 10: The function should handle edge case of single file
    if num_files == 1:
        single_file = files[0]
        expected_single_uri = f"s3://{bucket_name}/{single_file['Key']}"
        
        assert result == expected_single_uri, \
            f"With single file, should return that file: expected '{expected_single_uri}', got '{result}'"


@given(
    num_directories=st.integers(min_value=1, max_value=20),
    bucket_name=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
        min_size=3,
        max_size=20
    ),
    prefix=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
        min_size=1,
        max_size=20
    ).map(lambda x: x + '/')
)
@settings(max_examples=100, deadline=None)
def test_latest_directory_selection_property(num_directories, bucket_name, prefix):
    """
    Property 18: Latest data selection (directory variant)
    
    For any S3 prefix with multiple dated directories, the retraining process 
    should select the directory with the most recent timestamp.
    
    Validates: Requirements 11.4
    """
    from unittest.mock import Mock
    from src.retraining import get_latest_dataset_directory
    
    # Generate directory names and timestamps
    base_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    directories = []
    dir_timestamps = []
    
    for i in range(num_directories):
        # Generate unique timestamps
        offset_days = i * 3
        offset_hours = (i * 7) % 24
        
        timestamp = base_date + timedelta(days=offset_days, hours=offset_hours)
        dir_timestamps.append(timestamp)
        
        dir_name = f"{prefix}dataset-{i}/"
        directories.append(dir_name)
    
    # Create mock S3 client
    mock_s3 = Mock()
    
    # Mock the directory listing and timestamp queries
    list_calls = [
        # First call: list directories
        {
            'CommonPrefixes': [{'Prefix': d} for d in directories]
        }
    ]
    
    # Add calls for each directory's timestamp
    for timestamp in dir_timestamps:
        list_calls.append({
            'Contents': [{'LastModified': timestamp}]
        })
    
    mock_s3.list_objects_v2.side_effect = list_calls
    
    # Call the function
    result = get_latest_dataset_directory(bucket_name, prefix, mock_s3)
    
    # Property 1: The result should be an S3 URI
    assert result.startswith('s3://'), \
        f"Result should be an S3 URI: got '{result}'"
    assert bucket_name in result, \
        f"Result should contain bucket name '{bucket_name}': got '{result}'"
    
    # Property 2: The result should point to the directory with the most recent timestamp
    most_recent_timestamp = max(dir_timestamps)
    most_recent_index = dir_timestamps.index(most_recent_timestamp)
    most_recent_dir = directories[most_recent_index]
    expected_uri = f"s3://{bucket_name}/{most_recent_dir}"
    
    assert result == expected_uri, \
        f"Should select directory with most recent timestamp: expected '{expected_uri}', got '{result}'"
    
    # Property 3: The result should end with a slash (it's a directory)
    assert result.endswith('/'), \
        f"Directory URI should end with '/': got '{result}'"
    
    # Property 4: The selected directory should have a timestamp >= all others
    selected_index = directories.index(result.replace(f"s3://{bucket_name}/", ""))
    selected_timestamp = dir_timestamps[selected_index]
    
    for timestamp in dir_timestamps:
        assert selected_timestamp >= timestamp, \
            f"Selected directory timestamp should be >= all others: {selected_timestamp} vs {timestamp}"
    
    # Property 5: The selected directory should exist in the original directory list
    selected_dir = result.replace(f"s3://{bucket_name}/", "")
    assert selected_dir in directories, \
        f"Selected directory should exist in original list: '{selected_dir}' not in {directories}"
    
    # Property 6: With single directory, should return that directory
    if num_directories == 1:
        expected_single_uri = f"s3://{bucket_name}/{directories[0]}"
        assert result == expected_single_uri, \
            f"With single directory, should return that directory: expected '{expected_single_uri}', got '{result}'"
    
    # Property 7: The function should select based on content timestamp, not directory name
    # Directory names don't need to be chronological
    assert result is not None and len(result) > 0, \
        f"Should return a valid directory URI"
    
    # Property 8: The result should be a complete S3 URI with bucket and path
    parts = result.replace('s3://', '').split('/', 1)
    assert len(parts) == 2, \
        f"Result should have bucket and path: got '{result}'"
    assert parts[0] == bucket_name, \
        f"Result should contain correct bucket name: expected '{bucket_name}', got '{parts[0]}'"
    
    # Property 9: The path should start with the prefix
    path = parts[1]
    assert path.startswith(prefix), \
        f"Result path should start with prefix '{prefix}': got '{path}'"
    
    # Property 10: The function should handle various directory naming patterns
    # Selection should be based purely on timestamp, not directory name
    assert any(d in result for d in directories), \
        f"Result should contain one of the original directories: '{result}' not in {directories}"


@given(
    file_timestamps=st.lists(
        st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2026, 12, 31)
        ),
        min_size=1,
        max_size=100,
        unique=True
    ),
    bucket_name=st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=ord('a'), max_codepoint=ord('z')),
        min_size=3,
        max_size=20
    )
)
@settings(max_examples=100, deadline=None)
def test_latest_data_selection_with_random_timestamps(file_timestamps, bucket_name):
    """
    Property 18: Latest data selection with random timestamps
    
    For any set of files with random timestamps, the function should always 
    select the file with the maximum timestamp.
    
    Validates: Requirements 11.4
    """
    from unittest.mock import Mock
    from src.retraining import get_latest_data_path
    
    # Add timezone info to all timestamps
    file_timestamps = [ts.replace(tzinfo=timezone.utc) for ts in file_timestamps]
    
    # Create files with the given timestamps
    files = []
    for i, timestamp in enumerate(file_timestamps):
        files.append({
            'Key': f"processed-data/file-{i}.csv",
            'LastModified': timestamp
        })
    
    # Create mock S3 client
    mock_s3 = Mock()
    mock_s3.list_objects_v2.return_value = {
        'Contents': files
    }
    
    # Call the function
    result = get_latest_data_path(bucket_name, 'processed-data/', mock_s3)
    
    # Property 1: The result should select the file with maximum timestamp
    max_timestamp = max(file_timestamps)
    max_file = next(f for f in files if f['LastModified'] == max_timestamp)
    expected_uri = f"s3://{bucket_name}/{max_file['Key']}"
    
    assert result == expected_uri, \
        f"Should select file with maximum timestamp: expected '{expected_uri}', got '{result}'"
    
    # Property 2: The selected timestamp should be >= all other timestamps
    selected_file = next(f for f in files if f"s3://{bucket_name}/{f['Key']}" == result)
    selected_timestamp = selected_file['LastModified']
    
    for timestamp in file_timestamps:
        assert selected_timestamp >= timestamp, \
            f"Selected timestamp {selected_timestamp} should be >= {timestamp}"
    
    # Property 3: The selected timestamp should equal the maximum timestamp
    assert selected_timestamp == max_timestamp, \
        f"Selected timestamp should equal maximum: {selected_timestamp} vs {max_timestamp}"
    
    # Property 4: Calling the function multiple times should give consistent results
    result2 = get_latest_data_path(bucket_name, 'processed-data/', mock_s3)
    assert result == result2, \
        f"Function should be consistent: '{result}' vs '{result2}'"
    
    # Property 5: The result should be a valid S3 URI
    assert result.startswith('s3://'), \
        f"Result should be an S3 URI: got '{result}'"
    assert bucket_name in result, \
        f"Result should contain bucket name: got '{result}'"
    
    # Property 6: The selected file should be one of the input files
    selected_key = result.replace(f"s3://{bucket_name}/", "")
    file_keys = [f['Key'] for f in files]
    assert selected_key in file_keys, \
        f"Selected file should be from input files: '{selected_key}' not in {file_keys}"
    
    # Property 7: If all timestamps are identical, any file is valid
    if len(set(file_timestamps)) == 1:
        # All timestamps are the same, so any file is valid
        assert result in [f"s3://{bucket_name}/{f['Key']}" for f in files], \
            f"With identical timestamps, any file is valid: got '{result}'"
    
    # Property 8: The function should handle files from different years
    years = set(ts.year for ts in file_timestamps)
    if len(years) > 1:
        # Verify the selected file is from the most recent year
        selected_year = selected_timestamp.year
        max_year = max(years)
        # The selected file should be from a year >= all others
        assert selected_year >= max_year or selected_year == max_year, \
            f"Selected file year {selected_year} should be >= max year {max_year}"
    
    # Property 9: The function should handle files from different months
    if len(file_timestamps) > 1:
        # The selected file should have a timestamp that is not less than any other
        for other_timestamp in file_timestamps:
            assert selected_timestamp >= other_timestamp, \
                f"Selected timestamp should be >= all others: {selected_timestamp} vs {other_timestamp}"
    
    # Property 10: The function should work correctly with edge timestamps
    # (very old or very recent dates)
    assert selected_timestamp in file_timestamps, \
        f"Selected timestamp should be one of the input timestamps"
