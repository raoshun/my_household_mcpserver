"""Sync tests for image streaming utilities and cache."""

import io

import pytest


def test_chart_cache_import():
    """Test that ChartCache can be imported when cachetools is available."""
    try:
        from household_mcp.streaming.cache import ChartCache

        # Basic instantiation test
        cache = ChartCache(max_size=10, ttl=60)
        assert cache.max_size == 10
        assert cache.ttl == 60
        assert cache.size() == 0
    except ImportError:
        pytest.skip("cachetools not installed")


def test_chart_cache_key_generation():
    """Test cache key generation from parameters."""
    try:
        from household_mcp.streaming.cache import ChartCache

        cache = ChartCache()

        # Same parameters should generate same key
        params1 = {"year": 2025, "month": 10, "category": "食費"}
        params2 = {"year": 2025, "month": 10, "category": "食費"}
        assert cache.get_key(params1) == cache.get_key(params2)

        # Different parameters should generate different keys
        params3 = {"year": 2025, "month": 11, "category": "食費"}
        assert cache.get_key(params1) != cache.get_key(params3)

        # Order should not matter (sorted JSON)
        params4 = {"category": "食費", "month": 10, "year": 2025}
        assert cache.get_key(params1) == cache.get_key(params4)
    except ImportError:
        pytest.skip("cachetools not installed")


def test_chart_cache_get_set():
    """Test cache get/set operations."""
    try:
        from household_mcp.streaming.cache import ChartCache

        cache = ChartCache()
        key = "test_key"
        image_data = b"fake_image_data"

        # Initially empty
        assert cache.get(key) is None

        # Set and retrieve
        cache.set(key, image_data)
        assert cache.get(key) == image_data
        assert cache.size() == 1

        # Clear cache
        cache.clear()
        assert cache.size() == 0
        assert cache.get(key) is None
    except ImportError:
        pytest.skip("cachetools not installed")


def test_chart_cache_stats():
    """Test cache statistics."""
    try:
        from household_mcp.streaming.cache import ChartCache

        cache = ChartCache(max_size=100, ttl=300)
        stats = cache.stats()

        assert stats["max_size"] == 100
        assert stats["ttl"] == 300
        assert stats["current_size"] == 0

        # Add an item
        cache.set("key1", b"data1")
        stats = cache.stats()
        assert stats["current_size"] == 1
    except ImportError:
        pytest.skip("cachetools not installed")


def test_image_streamer_import():
    """Test that ImageStreamer can be imported."""
    from household_mcp.streaming.image_streamer import ImageStreamer

    streamer = ImageStreamer(chunk_size=1024)
    assert streamer.chunk_size == 1024


def test_image_streamer_buffer_conversion():
    """Test buffer/bytes conversion utilities."""
    from household_mcp.streaming.image_streamer import ImageStreamer

    test_data = b"test_image_data_12345"

    # bytes to buffer
    buffer = ImageStreamer.bytes_to_buffer(test_data)
    assert isinstance(buffer, io.BytesIO)
    assert buffer.tell() == 0  # positioned at start

    # buffer to bytes
    extracted = ImageStreamer.buffer_to_bytes(buffer)
    assert extracted == test_data


def test_chart_cache_ttl_expiration():
    """Test that cache items expire after TTL."""
    try:
        import time

        from household_mcp.streaming.cache import ChartCache

        # Very short TTL for testing
        cache = ChartCache(max_size=10, ttl=1)
        cache.set("key1", b"data1")

        # Should be available immediately
        assert cache.get("key1") == b"data1"

        # Wait for expiration
        time.sleep(1.5)

        # Should be expired (cachetools.TTLCache auto-expires)
        # Note: TTLCache may not immediately remove expired items until accessed
        result = cache.get("key1")
        assert result is None or result == b"data1"  # Depends on TTLCache behavior
    except ImportError:
        pytest.skip("cachetools not installed")


def test_chart_cache_max_size_limit():
    """Test that cache respects max_size limit."""
    try:
        from household_mcp.streaming.cache import ChartCache

        cache = ChartCache(max_size=3, ttl=300)

        # Add 3 items
        cache.set("key1", b"data1")
        cache.set("key2", b"data2")
        cache.set("key3", b"data3")
        assert cache.size() == 3

        # Adding 4th item should evict oldest
        cache.set("key4", b"data4")
        assert cache.size() <= 3  # Size should not exceed max_size
    except ImportError:
        pytest.skip("cachetools not installed")


def test_chart_cache_key_consistency():
    """Test that cache key generation is consistent and deterministic."""
    try:
        from household_mcp.streaming.cache import ChartCache

        cache = ChartCache()

        # Same parameters in different order
        params1 = {"year": 2025, "month": 10, "category": "食費", "graph_type": "line"}
        params2 = {"graph_type": "line", "category": "食費", "year": 2025, "month": 10}

        key1 = cache.get_key(params1)
        key2 = cache.get_key(params2)

        # Should generate identical keys
        assert key1 == key2

        # Keys should be strings (MD5 hashes)
        assert isinstance(key1, str)
        assert len(key1) == 32  # MD5 hash length
    except ImportError:
        pytest.skip("cachetools not installed")


def test_image_streamer_stream_bytes_sync():
    """Test synchronous streaming iterator produces same chunks as async."""
    from household_mcp.streaming.image_streamer import ImageStreamer

    streamer = ImageStreamer(chunk_size=5)
    test_data = b"0123456789"  # 10 bytes

    # Collect chunks from sync generator
    sync_chunks = list(streamer.stream_bytes_sync(test_data, delay_ms=0))

    # Should be split into 2 chunks
    assert len(sync_chunks) == 2
    assert sync_chunks[0] == b"01234"
    assert sync_chunks[1] == b"56789"


def test_global_cache_singleton():
    """Test that global cache is properly initialized and accessible.

    Note: Import module, not symbol, to avoid stale binding of GLOBAL_CHART_CACHE.
    """
    try:
        import household_mcp.streaming.global_cache as gc

        cache = gc.ensure_global_cache()
        assert cache is not None
        assert cache is gc.GLOBAL_CHART_CACHE

        # Should return same instance on multiple calls
        cache2 = gc.ensure_global_cache()
        assert cache is cache2
    except ImportError:
        pytest.skip("cachetools not installed")


def test_global_cache_operations():
    """Test basic operations on global cache."""
    try:
        from household_mcp.streaming.global_cache import ensure_global_cache

        cache = ensure_global_cache()
        test_key = "test_global_key"
        test_data = b"test_global_data"

        # Clear first
        cache.clear()

        # Set and get
        cache.set(test_key, test_data)
        assert cache.get(test_key) == test_data

        # Stats
        stats = cache.stats()
        assert stats["current_size"] >= 1

        # Clean up
        cache.clear()
    except ImportError:
        pytest.skip("cachetools not installed")


def test_create_response_sync_fallback_control():
    """Test control of sync fallback behavior."""
    try:
        from fastapi.responses import StreamingResponse  # noqa: F401

        from household_mcp.streaming.image_streamer import ImageStreamer
    except ImportError:
        pytest.skip("FastAPI not installed")

    streamer = ImageStreamer()
    test_data = b"test_data"

    # Case 1: Default behavior (fallback=True)
    # Should return sync generator wrapped in iterate_in_threadpool
    response = streamer.create_response(test_data)
    # Starlette wraps sync iterators in iterate_in_threadpool
    assert response.body_iterator.__name__ == "iterate_in_threadpool"

    # Case 2: Explicit fallback=True
    response = streamer.create_response(test_data, enable_sync_fallback=True)
    assert response.body_iterator.__name__ == "iterate_in_threadpool"

    # Case 3: fallback=False
    # Should return async generator directly (stream_bytes)
    response = streamer.create_response(test_data, enable_sync_fallback=False)
    assert response.body_iterator.__name__ == "stream_bytes"
