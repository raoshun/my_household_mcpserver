"""Tests for image streaming utilities."""

import io

import pytest

# Use asyncio only (trio not installed)
pytestmark = pytest.mark.asyncio


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


@pytest.mark.asyncio
async def test_image_streamer_stream_bytes():
    """Test async streaming of bytes."""
    from household_mcp.streaming.image_streamer import ImageStreamer

    streamer = ImageStreamer(chunk_size=5)
    test_data = b"0123456789"  # 10 bytes

    chunks = []
    async for chunk in streamer.stream_bytes(test_data, delay_ms=0):
        chunks.append(chunk)

    # Should be split into 2 chunks (5 bytes each)
    assert len(chunks) == 2
    assert chunks[0] == b"01234"
    assert chunks[1] == b"56789"


@pytest.mark.asyncio
async def test_image_streamer_stream_from_buffer():
    """Test async streaming from BytesIO buffer."""
    from household_mcp.streaming.image_streamer import ImageStreamer

    streamer = ImageStreamer(chunk_size=3)
    buffer = io.BytesIO(b"abcdefgh")  # 8 bytes

    chunks = []
    async for chunk in streamer.stream_from_buffer(buffer, delay_ms=0):
        chunks.append(chunk)

    # Should be split into 3 chunks
    assert len(chunks) == 3
    assert chunks[0] == b"abc"
    assert chunks[1] == b"def"
    assert chunks[2] == b"gh"
