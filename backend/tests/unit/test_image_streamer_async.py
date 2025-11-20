"""Async tests for image streaming utilities."""

import io
import pytest

# Use anyio for async tests
pytestmark = pytest.mark.anyio


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


async def test_image_streamer_empty_data():
    """Test streaming empty data."""
    from household_mcp.streaming.image_streamer import ImageStreamer

    streamer = ImageStreamer()
    chunks = []
    async for chunk in streamer.stream_bytes(b"", delay_ms=0):
        chunks.append(chunk)

    assert len(chunks) == 0


async def test_image_streamer_single_byte():
    """Test streaming single byte."""
    from household_mcp.streaming.image_streamer import ImageStreamer

    streamer = ImageStreamer(chunk_size=8192)
    chunks = []
    async for chunk in streamer.stream_bytes(b"X", delay_ms=0):
        chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0] == b"X"


async def test_image_streamer_large_image():
    """Test streaming large image data (NFR-005: memory efficiency)."""
    from household_mcp.streaming.image_streamer import ImageStreamer

    # Simulate 5MB image
    large_data = b"X" * (5 * 1024 * 1024)
    streamer = ImageStreamer(chunk_size=8192)

    chunk_count = 0
    total_size = 0
    async for chunk in streamer.stream_bytes(large_data, delay_ms=0):
        chunk_count += 1
        total_size += len(chunk)
        assert len(chunk) <= 8192  # Each chunk should not exceed chunk_size

    assert total_size == len(large_data)
    assert chunk_count > 1  # Should be chunked
