"""
Property-based tests for inference components.

These tests validate universal correctness properties across many generated inputs.
"""

import json
import sys
from pathlib import Path

from hypothesis import given, settings, strategies as st
import pytest

# Add src directory to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent / 'src'))


# Feature: aws-movielens-recommendation, Property 9: Endpoint accepts valid JSON input


@given(
    user_ids=st.lists(
        st.integers(min_value=0, max_value=10000),
        min_size=1,
        max_size=100
    ),
    movie_ids=st.lists(
        st.integers(min_value=0, max_value=5000),
        min_size=1,
        max_size=100
    )
)
@settings(max_examples=100, deadline=None)
def test_endpoint_accepts_valid_json_input(user_ids, movie_ids):
    """
    Property 9: Endpoint accepts valid JSON input
    
    For any valid JSON containing user_ids and movie_ids arrays, the endpoint 
    should accept the request without input validation errors.
    
    Validates: Requirements 5.2
    """
    from hypothesis import assume
    
    # Ensure both lists have the same length (requirement from input_fn)
    assume(len(user_ids) == len(movie_ids))
    
    # Import the input parsing function
    from inference import input_fn
    
    # Create valid JSON input
    input_data = {
        'user_ids': user_ids,
        'movie_ids': movie_ids
    }
    
    # Convert to JSON string
    request_body = json.dumps(input_data)
    
    # Property 1: Valid JSON with correct structure should be accepted without errors
    try:
        parsed_data = input_fn(request_body, content_type='application/json')
        success = True
    except ValueError as e:
        # If there's a ValueError, it should not be about JSON format or structure
        # (it could be about ID ranges, but that's checked in predict_fn)
        error_msg = str(e).lower()
        # These errors should NOT occur for valid JSON with correct structure
        invalid_errors = [
            'invalid json',
            'unsupported content type',
            'missing required field',
            'must be a list',
            'must be a json object',
            'length mismatch'
        ]
        assert not any(err in error_msg for err in invalid_errors), \
            f"Valid JSON should not raise structural validation errors, got: {e}"
        success = False
    
    # For valid JSON with correct structure, parsing should succeed
    assert success, \
        f"Valid JSON with user_ids and movie_ids should be accepted"
    
    # Property 2: Parsed data should contain the same user_ids
    assert 'user_ids' in parsed_data, \
        "Parsed data should contain 'user_ids' key"
    assert parsed_data['user_ids'] == user_ids, \
        f"Parsed user_ids should match input: expected {user_ids}, got {parsed_data['user_ids']}"
    
    # Property 3: Parsed data should contain the same movie_ids
    assert 'movie_ids' in parsed_data, \
        "Parsed data should contain 'movie_ids' key"
    assert parsed_data['movie_ids'] == movie_ids, \
        f"Parsed movie_ids should match input: expected {movie_ids}, got {parsed_data['movie_ids']}"
    
    # Property 4: Parsed data should be a dictionary
    assert isinstance(parsed_data, dict), \
        f"Parsed data should be a dictionary, got {type(parsed_data)}"
    
    # Property 5: Parsed data should have exactly 2 keys
    assert len(parsed_data) == 2, \
        f"Parsed data should have exactly 2 keys (user_ids, movie_ids), got {len(parsed_data)}"
    
    # Property 6: Parsed lists should have the same length as input
    assert len(parsed_data['user_ids']) == len(user_ids), \
        f"Parsed user_ids length should match input length"
    assert len(parsed_data['movie_ids']) == len(movie_ids), \
        f"Parsed movie_ids length should match input length"
    
    # Property 7: Parsed lists should be lists (not tuples or other sequences)
    assert isinstance(parsed_data['user_ids'], list), \
        f"Parsed user_ids should be a list, got {type(parsed_data['user_ids'])}"
    assert isinstance(parsed_data['movie_ids'], list), \
        f"Parsed movie_ids should be a list, got {type(parsed_data['movie_ids'])}"
    
    # Property 8: All elements in parsed lists should be integers
    assert all(isinstance(uid, int) for uid in parsed_data['user_ids']), \
        "All user_ids should be integers"
    assert all(isinstance(mid, int) for mid in parsed_data['movie_ids']), \
        "All movie_ids should be integers"
    
    # Property 9: All elements should be non-negative (as validated by input_fn)
    assert all(uid >= 0 for uid in parsed_data['user_ids']), \
        "All user_ids should be non-negative"
    assert all(mid >= 0 for mid in parsed_data['movie_ids']), \
        "All movie_ids should be non-negative"
    
    # Property 10: Parsing should be idempotent - parsing the same JSON twice gives same result
    parsed_data_2 = input_fn(request_body, content_type='application/json')
    assert parsed_data == parsed_data_2, \
        "Parsing the same JSON twice should give identical results"
    
    # Property 11: The function should accept 'application/json' content type
    # (already tested above, but let's be explicit)
    parsed_with_explicit_type = input_fn(request_body, content_type='application/json')
    assert parsed_with_explicit_type == parsed_data, \
        "Parsing with explicit 'application/json' content type should work"
    
    # Property 12: Order of elements should be preserved
    for i in range(len(user_ids)):
        assert parsed_data['user_ids'][i] == user_ids[i], \
            f"Order of user_ids should be preserved at index {i}"
        assert parsed_data['movie_ids'][i] == movie_ids[i], \
            f"Order of movie_ids should be preserved at index {i}"
    
    # Property 13: Empty lists should not be accepted (as per input_fn validation)
    # This is tested separately, but we verify our test data is non-empty
    assert len(user_ids) > 0, "Test should use non-empty user_ids"
    assert len(movie_ids) > 0, "Test should use non-empty movie_ids"
    
    # Property 14: The parsed data should be usable for prediction
    # (i.e., it has the correct structure expected by predict_fn)
    assert set(parsed_data.keys()) == {'user_ids', 'movie_ids'}, \
        "Parsed data should have exactly the keys expected by predict_fn"


# Feature: aws-movielens-recommendation, Property 10: Endpoint returns valid JSON output


@given(
    predictions=st.lists(
        st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False),
        min_size=1,
        max_size=100
    )
)
@settings(max_examples=100, deadline=None)
def test_endpoint_returns_valid_json_output(predictions):
    """
    Property 10: Endpoint returns valid JSON output
    
    For any valid prediction request, the endpoint should return JSON containing 
    a predictions array with the same length as the input arrays.
    
    Validates: Requirements 5.3
    """
    # Import the output formatting function
    from inference import output_fn
    
    # Property 1: output_fn should accept a list of predictions
    try:
        response_body = output_fn(predictions, accept='application/json')
        success = True
    except Exception as e:
        pytest.fail(f"output_fn should accept valid predictions list without errors, got: {e}")
    
    # Property 2: Response should be a string (JSON string)
    assert isinstance(response_body, str), \
        f"Response body should be a string, got {type(response_body)}"
    
    # Property 3: Response should be valid JSON
    try:
        parsed_response = json.loads(response_body)
    except json.JSONDecodeError as e:
        pytest.fail(f"Response should be valid JSON, got decode error: {e}")
    
    # Property 4: Parsed response should be a dictionary
    assert isinstance(parsed_response, dict), \
        f"Parsed response should be a dictionary, got {type(parsed_response)}"
    
    # Property 5: Response should contain 'predictions' key
    assert 'predictions' in parsed_response, \
        "Response should contain 'predictions' key"
    
    # Property 6: Response should have exactly 1 key
    assert len(parsed_response) == 1, \
        f"Response should have exactly 1 key (predictions), got {len(parsed_response)} keys: {list(parsed_response.keys())}"
    
    # Property 7: 'predictions' value should be a list
    assert isinstance(parsed_response['predictions'], list), \
        f"'predictions' should be a list, got {type(parsed_response['predictions'])}"
    
    # Property 8: Length of predictions in response should match input length
    assert len(parsed_response['predictions']) == len(predictions), \
        f"Response predictions length should match input length: expected {len(predictions)}, got {len(parsed_response['predictions'])}"
    
    # Property 9: All predictions in response should be numbers
    for i, pred in enumerate(parsed_response['predictions']):
        assert isinstance(pred, (int, float)), \
            f"predictions[{i}] should be a number, got {type(pred)}"
    
    # Property 10: Predictions should match input predictions (within floating point precision)
    for i in range(len(predictions)):
        expected = predictions[i]
        actual = parsed_response['predictions'][i]
        # Allow for small floating point differences due to JSON serialization
        assert abs(actual - expected) < 1e-6, \
            f"predictions[{i}] should match input: expected {expected}, got {actual}"
    
    # Property 11: Order of predictions should be preserved
    for i in range(len(predictions)):
        assert parsed_response['predictions'][i] == predictions[i] or \
               abs(parsed_response['predictions'][i] - predictions[i]) < 1e-6, \
            f"Order of predictions should be preserved at index {i}"
    
    # Property 12: Formatting should be idempotent - formatting the same predictions twice gives same result
    response_body_2 = output_fn(predictions, accept='application/json')
    assert response_body == response_body_2, \
        "Formatting the same predictions twice should give identical JSON strings"
    
    # Property 13: The function should accept 'application/json' accept type
    response_with_explicit_type = output_fn(predictions, accept='application/json')
    assert response_with_explicit_type == response_body, \
        "Formatting with explicit 'application/json' accept type should work"
    
    # Property 14: Response should be parseable back to the same structure
    reparsed = json.loads(response_body)
    assert reparsed == parsed_response, \
        "Re-parsing the JSON should give the same structure"
    
    # Property 15: Empty predictions list should be handled correctly
    # (This is tested separately, but we verify our test data is non-empty)
    assert len(predictions) > 0, "Test should use non-empty predictions"
    
    # Property 16: Response should not contain any extra fields
    assert set(parsed_response.keys()) == {'predictions'}, \
        f"Response should only contain 'predictions' key, got: {list(parsed_response.keys())}"
    
    # Property 17: All predictions should be finite numbers (no NaN or Infinity)
    for i, pred in enumerate(parsed_response['predictions']):
        if isinstance(pred, float):
            assert not (pred != pred), \
                f"predictions[{i}] should not be NaN"
            assert pred != float('inf') and pred != float('-inf'), \
                f"predictions[{i}] should not be infinity"
    
    # Property 18: JSON should be compact (no unnecessary whitespace)
    # This is a reasonable expectation for API responses
    assert '\n' not in response_body or response_body.count('\n') < 2, \
        "JSON response should be compact (minimal whitespace)"
    
    # Property 19: Response can be round-tripped through JSON
    round_trip = json.dumps(json.loads(response_body))
    parsed_round_trip = json.loads(round_trip)
    assert parsed_round_trip == parsed_response, \
        "Response should survive JSON round-trip"
    
    # Property 20: The response structure matches the expected API contract
    # Expected format: {"predictions": [float, float, ...]}
    assert isinstance(parsed_response, dict), "Response should be a dict"
    assert 'predictions' in parsed_response, "Response should have 'predictions' key"
    assert isinstance(parsed_response['predictions'], list), "'predictions' should be a list"
    assert all(isinstance(p, (int, float)) for p in parsed_response['predictions']), \
        "All predictions should be numbers"


# Feature: aws-movielens-recommendation, Property 11: Batch prediction consistency


@given(
    user_ids=st.lists(
        st.integers(min_value=0, max_value=100),
        min_size=1,
        max_size=20
    ),
    movie_ids=st.lists(
        st.integers(min_value=0, max_value=50),
        min_size=1,
        max_size=20
    ),
    embedding_dim=st.integers(min_value=8, max_value=32)
)
@settings(max_examples=100, deadline=None)
def test_batch_prediction_consistency(user_ids, movie_ids, embedding_dim):
    """
    Property 11: Batch prediction consistency
    
    For any set of individual prediction requests, making them as a batch should 
    return the same predictions as making them individually (in the same order).
    
    Validates: Requirements 14.4
    """
    from hypothesis import assume
    import torch
    
    # Ensure both lists have the same length
    assume(len(user_ids) == len(movie_ids))
    
    # Import required functions and model
    from inference import predict_fn
    from model import CollaborativeFilteringModel
    
    # Create a model for testing
    # Use small dimensions to keep test fast
    num_users = max(user_ids) + 10  # Ensure all user IDs are valid
    num_movies = max(movie_ids) + 10  # Ensure all movie IDs are valid
    
    model = CollaborativeFilteringModel(
        num_users=num_users,
        num_movies=num_movies,
        embedding_dim=embedding_dim
    )
    model.eval()
    
    # Property 1: Making predictions as a batch
    batch_input = {
        'user_ids': user_ids,
        'movie_ids': movie_ids
    }
    
    batch_predictions = predict_fn(batch_input, model)
    
    # Property 2: Making predictions individually
    individual_predictions = []
    for user_id, movie_id in zip(user_ids, movie_ids):
        individual_input = {
            'user_ids': [user_id],
            'movie_ids': [movie_id]
        }
        individual_pred = predict_fn(individual_input, model)
        individual_predictions.extend(individual_pred)
    
    # Property 3: Batch predictions should have the same length as input
    assert len(batch_predictions) == len(user_ids), \
        f"Batch predictions length should match input length: expected {len(user_ids)}, got {len(batch_predictions)}"
    
    # Property 4: Individual predictions should have the same length as input
    assert len(individual_predictions) == len(user_ids), \
        f"Individual predictions length should match input length: expected {len(user_ids)}, got {len(individual_predictions)}"
    
    # Property 5: Batch and individual predictions should have the same length
    assert len(batch_predictions) == len(individual_predictions), \
        f"Batch and individual predictions should have same length: batch={len(batch_predictions)}, individual={len(individual_predictions)}"
    
    # Property 6: Each prediction in batch should match corresponding individual prediction
    for i in range(len(user_ids)):
        batch_pred = batch_predictions[i]
        individual_pred = individual_predictions[i]
        
        # Allow for small floating point differences
        assert abs(batch_pred - individual_pred) < 1e-5, \
            f"Prediction {i} should be consistent: batch={batch_pred}, individual={individual_pred}, diff={abs(batch_pred - individual_pred)}"
    
    # Property 7: Order should be preserved
    # The i-th prediction in batch should correspond to the i-th (user_id, movie_id) pair
    for i in range(len(user_ids)):
        # Verify by making a single prediction for this specific pair
        single_input = {
            'user_ids': [user_ids[i]],
            'movie_ids': [movie_ids[i]]
        }
        single_pred = predict_fn(single_input, model)[0]
        
        assert abs(batch_predictions[i] - single_pred) < 1e-5, \
            f"Batch prediction {i} should match single prediction for (user={user_ids[i]}, movie={movie_ids[i]}): batch={batch_predictions[i]}, single={single_pred}"
    
    # Property 8: All predictions should be finite numbers
    for i, pred in enumerate(batch_predictions):
        assert isinstance(pred, (int, float)), \
            f"Batch prediction {i} should be a number, got {type(pred)}"
        if isinstance(pred, float):
            assert not (pred != pred), \
                f"Batch prediction {i} should not be NaN"
            assert pred != float('inf') and pred != float('-inf'), \
                f"Batch prediction {i} should not be infinity"
    
    for i, pred in enumerate(individual_predictions):
        assert isinstance(pred, (int, float)), \
            f"Individual prediction {i} should be a number, got {type(pred)}"
        if isinstance(pred, float):
            assert not (pred != pred), \
                f"Individual prediction {i} should not be NaN"
            assert pred != float('inf') and pred != float('-inf'), \
                f"Individual prediction {i} should not be infinity"
    
    # Property 9: Predictions should be deterministic
    # Making the same batch prediction twice should give identical results
    batch_predictions_2 = predict_fn(batch_input, model)
    assert len(batch_predictions) == len(batch_predictions_2), \
        "Repeated batch predictions should have same length"
    
    for i in range(len(batch_predictions)):
        assert abs(batch_predictions[i] - batch_predictions_2[i]) < 1e-10, \
            f"Repeated batch prediction {i} should be identical: first={batch_predictions[i]}, second={batch_predictions_2[i]}"
    
    # Property 10: Empty batch should not be tested (input validation prevents this)
    assert len(user_ids) > 0, "Test should use non-empty input"
    
    # Property 11: Single-element batch should work correctly
    if len(user_ids) == 1:
        single_batch_input = {
            'user_ids': [user_ids[0]],
            'movie_ids': [movie_ids[0]]
        }
        single_batch_pred = predict_fn(single_batch_input, model)
        assert len(single_batch_pred) == 1, \
            "Single-element batch should return single prediction"
        assert abs(single_batch_pred[0] - batch_predictions[0]) < 1e-10, \
            "Single-element batch prediction should match"
    
    # Property 12: Batch predictions should be independent of batch size
    # Split the batch into two halves and verify consistency
    if len(user_ids) > 1:
        mid = len(user_ids) // 2
        
        first_half_input = {
            'user_ids': user_ids[:mid],
            'movie_ids': movie_ids[:mid]
        }
        second_half_input = {
            'user_ids': user_ids[mid:],
            'movie_ids': movie_ids[mid:]
        }
        
        first_half_preds = predict_fn(first_half_input, model)
        second_half_preds = predict_fn(second_half_input, model)
        
        combined_preds = first_half_preds + second_half_preds
        
        assert len(combined_preds) == len(batch_predictions), \
            "Combined predictions should have same length as batch predictions"
        
        for i in range(len(batch_predictions)):
            assert abs(combined_preds[i] - batch_predictions[i]) < 1e-5, \
                f"Split batch prediction {i} should match full batch: split={combined_preds[i]}, batch={batch_predictions[i]}"
    
    # Property 13: Predictions should not depend on the order of other predictions in the batch
    # (i.e., the prediction for (user_i, movie_i) should be the same regardless of what other pairs are in the batch)
    # This is implicitly tested by comparing batch to individual predictions
    
    # Property 14: All predictions should be of the same type
    pred_types = set(type(p) for p in batch_predictions)
    assert len(pred_types) == 1, \
        f"All batch predictions should have the same type, got {pred_types}"
    
    pred_types_individual = set(type(p) for p in individual_predictions)
    assert len(pred_types_individual) == 1, \
        f"All individual predictions should have the same type, got {pred_types_individual}"
    
    # Property 15: Batch and individual predictions should have the same type
    assert pred_types == pred_types_individual, \
        f"Batch and individual predictions should have same type: batch={pred_types}, individual={pred_types_individual}"


# Feature: aws-movielens-recommendation, Property 12: Caching returns identical results


@given(
    user_ids=st.lists(
        st.integers(min_value=0, max_value=100),
        min_size=1,
        max_size=20
    ),
    movie_ids=st.lists(
        st.integers(min_value=0, max_value=50),
        min_size=1,
        max_size=20
    ),
    embedding_dim=st.integers(min_value=8, max_value=32)
)
@settings(max_examples=100, deadline=None)
def test_caching_returns_identical_results(user_ids, movie_ids, embedding_dim):
    """
    Property 12: Caching returns identical results
    
    For any prediction request made twice with identical inputs, the second request 
    should return the same prediction as the first (demonstrating cache consistency).
    
    Validates: Requirements 14.5
    """
    from hypothesis import assume
    import torch
    
    # Ensure both lists have the same length
    assume(len(user_ids) == len(movie_ids))
    
    # Import required functions and model
    from inference import predict_fn, get_cache
    from model import CollaborativeFilteringModel
    
    # Clear cache before test to ensure clean state
    cache = get_cache()
    cache.clear()
    
    # Create a model for testing
    num_users = max(user_ids) + 10  # Ensure all user IDs are valid
    num_movies = max(movie_ids) + 10  # Ensure all movie IDs are valid
    
    model = CollaborativeFilteringModel(
        num_users=num_users,
        num_movies=num_movies,
        embedding_dim=embedding_dim
    )
    model.eval()
    
    # Property 1: First prediction request (cache miss)
    input_data = {
        'user_ids': user_ids,
        'movie_ids': movie_ids
    }
    
    first_predictions = predict_fn(input_data, model)
    
    # Property 2: Second prediction request with identical inputs (cache hit)
    second_predictions = predict_fn(input_data, model)
    
    # Property 3: Both predictions should have the same length
    assert len(first_predictions) == len(second_predictions), \
        f"First and second predictions should have same length: first={len(first_predictions)}, second={len(second_predictions)}"
    
    # Property 4: Both predictions should have the same length as input
    assert len(first_predictions) == len(user_ids), \
        f"Predictions length should match input length: expected {len(user_ids)}, got {len(first_predictions)}"
    
    # Property 5: Each prediction should be identical between first and second request
    for i in range(len(user_ids)):
        first_pred = first_predictions[i]
        second_pred = second_predictions[i]
        
        # Cached predictions should be EXACTLY identical (not just close)
        assert first_pred == second_pred, \
            f"Prediction {i} for (user={user_ids[i]}, movie={movie_ids[i]}) should be identical: first={first_pred}, second={second_pred}"
    
    # Property 6: Cache should have entries after predictions
    cache_stats = cache.get_stats()
    assert cache_stats['size'] > 0, \
        "Cache should contain entries after predictions"
    
    # Property 7: Cache should have recorded hits on second request
    # After first request, all entries are cached
    # After second request, we should have hits
    assert cache_stats['hits'] > 0, \
        f"Cache should have recorded hits on second request, got {cache_stats['hits']} hits"
    
    # Property 8: Number of cache entries should not exceed number of unique (user, movie) pairs
    unique_pairs = len(set(zip(user_ids, movie_ids)))
    assert cache_stats['size'] <= unique_pairs, \
        f"Cache size should not exceed unique pairs: cache_size={cache_stats['size']}, unique_pairs={unique_pairs}"
    
    # Property 9: Third request should also return identical results
    third_predictions = predict_fn(input_data, model)
    
    for i in range(len(user_ids)):
        assert first_predictions[i] == third_predictions[i], \
            f"Prediction {i} should be identical on third request: first={first_predictions[i]}, third={third_predictions[i]}"
    
    # Property 10: Cache hit rate should increase with repeated requests
    cache_stats_after_third = cache.get_stats()
    assert cache_stats_after_third['hits'] > cache_stats['hits'], \
        f"Cache hits should increase after third request: before={cache_stats['hits']}, after={cache_stats_after_third['hits']}"
    
    # Property 11: Predictions should be deterministic regardless of cache state
    # Clear cache and make prediction again
    cache.clear()
    fourth_predictions = predict_fn(input_data, model)
    
    for i in range(len(user_ids)):
        assert first_predictions[i] == fourth_predictions[i], \
            f"Prediction {i} should be identical after cache clear: first={first_predictions[i]}, fourth={fourth_predictions[i]}"
    
    # Property 12: Individual predictions should be cached correctly
    # Make individual predictions and verify they're cached
    if len(user_ids) > 0:
        cache.clear()
        
        # Make first individual prediction
        single_input = {
            'user_ids': [user_ids[0]],
            'movie_ids': [movie_ids[0]]
        }
        
        first_single = predict_fn(single_input, model)[0]
        second_single = predict_fn(single_input, model)[0]
        
        assert first_single == second_single, \
            f"Individual prediction should be identical when cached: first={first_single}, second={second_single}"
    
    # Property 13: Cache should handle duplicate pairs in same request correctly
    if len(user_ids) > 1:
        cache.clear()
        
        # Create input with duplicate pairs
        duplicate_user_ids = [user_ids[0], user_ids[0]]
        duplicate_movie_ids = [movie_ids[0], movie_ids[0]]
        
        duplicate_input = {
            'user_ids': duplicate_user_ids,
            'movie_ids': duplicate_movie_ids
        }
        
        duplicate_predictions = predict_fn(duplicate_input, model)
        
        # Both predictions should be identical (same input pair)
        assert duplicate_predictions[0] == duplicate_predictions[1], \
            f"Duplicate pairs should return identical predictions: first={duplicate_predictions[0]}, second={duplicate_predictions[1]}"
    
    # Property 14: Cache should not affect prediction accuracy
    # Predictions from cache should be exactly the same as fresh predictions
    cache.clear()
    fresh_predictions = predict_fn(input_data, model)
    cached_predictions = predict_fn(input_data, model)
    
    for i in range(len(user_ids)):
        assert fresh_predictions[i] == cached_predictions[i], \
            f"Cached prediction {i} should match fresh prediction: fresh={fresh_predictions[i]}, cached={cached_predictions[i]}"
    
    # Property 15: Cache should handle mixed cached and uncached requests
    if len(user_ids) > 2:
        cache.clear()
        
        # Cache first half
        first_half_input = {
            'user_ids': user_ids[:len(user_ids)//2],
            'movie_ids': movie_ids[:len(movie_ids)//2]
        }
        first_half_preds = predict_fn(first_half_input, model)
        
        # Now make full request (first half cached, second half uncached)
        full_preds = predict_fn(input_data, model)
        
        # First half should match
        for i in range(len(first_half_preds)):
            assert first_half_preds[i] == full_preds[i], \
                f"Cached prediction {i} in mixed request should match: cached={first_half_preds[i]}, mixed={full_preds[i]}"
    
    # Property 16: All predictions should be finite numbers
    for i, pred in enumerate(first_predictions):
        assert isinstance(pred, (int, float)), \
            f"Prediction {i} should be a number, got {type(pred)}"
        if isinstance(pred, float):
            assert not (pred != pred), \
                f"Prediction {i} should not be NaN"
            assert pred != float('inf') and pred != float('-inf'), \
                f"Prediction {i} should not be infinity"
    
    # Property 17: Cache statistics should be consistent
    final_stats = cache.get_stats()
    assert final_stats['hits'] >= 0, "Cache hits should be non-negative"
    assert final_stats['misses'] >= 0, "Cache misses should be non-negative"
    assert final_stats['size'] >= 0, "Cache size should be non-negative"
    assert final_stats['size'] <= final_stats['max_size'], \
        f"Cache size should not exceed max size: size={final_stats['size']}, max={final_stats['max_size']}"
    
    # Property 18: Cache hit rate should be calculable
    total_requests = final_stats['hits'] + final_stats['misses']
    if total_requests > 0:
        expected_hit_rate = final_stats['hits'] / total_requests
        assert abs(final_stats['hit_rate'] - expected_hit_rate) < 1e-10, \
            f"Cache hit rate should be correctly calculated: expected={expected_hit_rate}, got={final_stats['hit_rate']}"
    
    # Property 19: Clearing cache should reset statistics
    cache.clear()
    cleared_stats = cache.get_stats()
    assert cleared_stats['hits'] == 0, "Cache hits should be 0 after clear"
    assert cleared_stats['misses'] == 0, "Cache misses should be 0 after clear"
    assert cleared_stats['size'] == 0, "Cache size should be 0 after clear"
    assert cleared_stats['hit_rate'] == 0.0, "Cache hit rate should be 0.0 after clear"
    
    # Property 20: Cache should work correctly after being cleared and reused
    post_clear_predictions = predict_fn(input_data, model)
    
    for i in range(len(user_ids)):
        assert first_predictions[i] == post_clear_predictions[i], \
            f"Prediction {i} should be identical after cache clear and reuse: first={first_predictions[i]}, post_clear={post_clear_predictions[i]}"
