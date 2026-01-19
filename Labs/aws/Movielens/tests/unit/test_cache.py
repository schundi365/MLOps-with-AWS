"""
Unit tests for the LRUCache class

Tests cover:
- Cache hit behavior
- Cache miss behavior
- Cache eviction (LRU policy)

Validates: Requirements 14.5
"""

import pytest

from src.inference import LRUCache


class TestLRUCache:
    """Unit tests for LRUCache class"""
    
    def test_cache_hit(self):
        """Test cache hit returns stored value"""
        cache = LRUCache(max_size=10)
        
        # Store a value
        cache.put((1, 2), 4.5)
        
        # Retrieve it (cache hit)
        result = cache.get((1, 2))
        
        assert result == 4.5
        assert cache.hits == 1
        assert cache.misses == 0
    
    def test_cache_miss(self):
        """Test cache miss returns None"""
        cache = LRUCache(max_size=10)
        
        # Try to get a value that doesn't exist
        result = cache.get((1, 2))
        
        assert result is None
        assert cache.hits == 0
        assert cache.misses == 1
    
    def test_cache_eviction_lru_policy(self):
        """Test cache evicts least recently used entry when full"""
        cache = LRUCache(max_size=3)
        
        # Fill cache to capacity
        cache.put((1, 1), 1.0)
        cache.put((2, 2), 2.0)
        cache.put((3, 3), 3.0)
        
        # Verify all entries are in cache
        assert cache.get((1, 1)) == 1.0
        assert cache.get((2, 2)) == 2.0
        assert cache.get((3, 3)) == 3.0
        
        # Add one more entry, should evict (1, 1) as it's least recently used
        cache.put((4, 4), 4.0)
        
        # Verify (1, 1) was evicted
        assert cache.get((1, 1)) is None
        
        # Verify other entries are still present
        assert cache.get((2, 2)) == 2.0
        assert cache.get((3, 3)) == 3.0
        assert cache.get((4, 4)) == 4.0
        
        # Verify cache size is at max
        assert len(cache.cache) == 3
    
    def test_cache_eviction_updates_lru_order(self):
        """Test that accessing an entry updates its LRU position"""
        cache = LRUCache(max_size=3)
        
        # Fill cache
        cache.put((1, 1), 1.0)
        cache.put((2, 2), 2.0)
        cache.put((3, 3), 3.0)
        
        # Access (1, 1) to make it most recently used
        cache.get((1, 1))
        
        # Add new entry, should evict (2, 2) as it's now least recently used
        cache.put((4, 4), 4.0)
        
        # Verify (2, 2) was evicted, not (1, 1)
        assert cache.get((2, 2)) is None
        assert cache.get((1, 1)) == 1.0
        assert cache.get((3, 3)) == 3.0
        assert cache.get((4, 4)) == 4.0
    
    def test_cache_update_existing_entry(self):
        """Test updating an existing cache entry"""
        cache = LRUCache(max_size=10)
        
        # Store initial value
        cache.put((1, 2), 4.5)
        
        # Update with new value
        cache.put((1, 2), 5.0)
        
        # Verify updated value is returned
        result = cache.get((1, 2))
        assert result == 5.0
        
        # Verify cache size didn't increase
        assert len(cache.cache) == 1
    
    def test_cache_multiple_hits(self):
        """Test multiple cache hits increment hit counter"""
        cache = LRUCache(max_size=10)
        
        cache.put((1, 2), 4.5)
        
        # Multiple hits
        cache.get((1, 2))
        cache.get((1, 2))
        cache.get((1, 2))
        
        assert cache.hits == 3
        assert cache.misses == 0
    
    def test_cache_multiple_misses(self):
        """Test multiple cache misses increment miss counter"""
        cache = LRUCache(max_size=10)
        
        # Multiple misses
        cache.get((1, 2))
        cache.get((3, 4))
        cache.get((5, 6))
        
        assert cache.hits == 0
        assert cache.misses == 3
    
    def test_cache_mixed_hits_and_misses(self):
        """Test cache correctly tracks mixed hits and misses"""
        cache = LRUCache(max_size=10)
        
        cache.put((1, 2), 4.5)
        cache.put((3, 4), 3.8)
        
        # Mix of hits and misses
        cache.get((1, 2))  # Hit
        cache.get((5, 6))  # Miss
        cache.get((3, 4))  # Hit
        cache.get((7, 8))  # Miss
        
        assert cache.hits == 2
        assert cache.misses == 2
    
    def test_cache_get_stats(self):
        """Test cache statistics are calculated correctly"""
        cache = LRUCache(max_size=10)
        
        cache.put((1, 2), 4.5)
        cache.put((3, 4), 3.8)
        
        cache.get((1, 2))  # Hit
        cache.get((5, 6))  # Miss
        cache.get((3, 4))  # Hit
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 2
        assert stats['misses'] == 1
        assert stats['size'] == 2
        assert stats['max_size'] == 10
        assert stats['hit_rate'] == 2.0 / 3.0
    
    def test_cache_clear(self):
        """Test cache clear removes all entries and resets stats"""
        cache = LRUCache(max_size=10)
        
        # Add entries and generate stats
        cache.put((1, 2), 4.5)
        cache.put((3, 4), 3.8)
        cache.get((1, 2))
        cache.get((5, 6))
        
        # Clear cache
        cache.clear()
        
        # Verify cache is empty
        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0
        
        # Verify cleared entries are gone
        assert cache.get((1, 2)) is None
        assert cache.get((3, 4)) is None
    
    def test_cache_empty_stats(self):
        """Test statistics for empty cache"""
        cache = LRUCache(max_size=10)
        
        stats = cache.get_stats()
        
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['size'] == 0
        assert stats['max_size'] == 10
        assert stats['hit_rate'] == 0.0
    
    def test_cache_size_limit_enforced(self):
        """Test cache never exceeds max_size"""
        cache = LRUCache(max_size=5)
        
        # Add more entries than max_size
        for i in range(10):
            cache.put((i, i), float(i))
        
        # Verify cache size is at max
        assert len(cache.cache) == 5
        
        # Verify only the last 5 entries are present
        for i in range(5, 10):
            assert cache.get((i, i)) == float(i)
        
        # Verify first 5 entries were evicted
        for i in range(5):
            assert cache.get((i, i)) is None
    
    def test_cache_single_entry_capacity(self):
        """Test cache with capacity of 1"""
        cache = LRUCache(max_size=1)
        
        cache.put((1, 1), 1.0)
        assert cache.get((1, 1)) == 1.0
        
        # Add another entry, should evict first
        cache.put((2, 2), 2.0)
        assert cache.get((1, 1)) is None
        assert cache.get((2, 2)) == 2.0
        
        # Verify size is 1
        assert len(cache.cache) == 1
    
    def test_cache_different_key_types(self):
        """Test cache works with different tuple keys"""
        cache = LRUCache(max_size=10)
        
        # Test with different user_id and movie_id combinations
        cache.put((0, 0), 1.0)
        cache.put((999, 999), 2.0)
        cache.put((123, 456), 3.0)
        
        assert cache.get((0, 0)) == 1.0
        assert cache.get((999, 999)) == 2.0
        assert cache.get((123, 456)) == 3.0
    
    def test_cache_value_types(self):
        """Test cache stores different float values correctly"""
        cache = LRUCache(max_size=10)
        
        # Test with different float values
        cache.put((1, 1), 0.0)
        cache.put((2, 2), 5.0)
        cache.put((3, 3), 4.999999)
        cache.put((4, 4), -1.5)
        
        assert cache.get((1, 1)) == 0.0
        assert cache.get((2, 2)) == 5.0
        assert cache.get((3, 3)) == 4.999999
        assert cache.get((4, 4)) == -1.5
    
    def test_cache_eviction_order_fifo_when_no_access(self):
        """Test eviction follows FIFO when entries are not accessed"""
        cache = LRUCache(max_size=3)
        
        # Add entries without accessing them
        cache.put((1, 1), 1.0)
        cache.put((2, 2), 2.0)
        cache.put((3, 3), 3.0)
        
        # Add fourth entry, should evict first (FIFO)
        cache.put((4, 4), 4.0)
        
        assert cache.get((1, 1)) is None
        assert cache.get((2, 2)) == 2.0
        assert cache.get((3, 3)) == 3.0
        assert cache.get((4, 4)) == 4.0
    
    def test_cache_put_updates_lru_position(self):
        """Test that putting an existing key updates its LRU position"""
        cache = LRUCache(max_size=3)
        
        cache.put((1, 1), 1.0)
        cache.put((2, 2), 2.0)
        cache.put((3, 3), 3.0)
        
        # Update (1, 1) to make it most recently used
        cache.put((1, 1), 1.5)
        
        # Add new entry, should evict (2, 2) as it's now least recently used
        cache.put((4, 4), 4.0)
        
        assert cache.get((2, 2)) is None
        assert cache.get((1, 1)) == 1.5
        assert cache.get((3, 3)) == 3.0
        assert cache.get((4, 4)) == 4.0
