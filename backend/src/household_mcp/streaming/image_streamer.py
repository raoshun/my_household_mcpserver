"""
Image streaming utilities for HTTP delivery.

This module provides utilities for streaming chart images over HTTP.
"""

from __future__ import annotations

import asyncio
import io
from collections.abc import AsyncGenerator

try:
    from fastapi.responses import StreamingResponse

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


class ImageStreamer:
    """
    Utility for streaming images over HTTP.

    Provides chunked streaming to reduce memory pressure and
    improve response times for large images.
    """

    def __init__(self, chunk_size: int = 8192):
        """
        Initialize image streamer.

        Args:
            chunk_size: Size of chunks in bytes (default: 8192 = 8KB)

        """
        self.chunk_size = chunk_size

    async def stream_bytes(
        self, image_data: bytes, delay_ms: float = 0.01
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream image data in chunks.

        Args:
            image_data: Complete image data as bytes
            delay_ms: Delay between chunks in seconds (default: 0.01)
                     Helps prevent CPU saturation

        Yields:
            Chunks of image_data

        """
        for i in range(0, len(image_data), self.chunk_size):
            chunk = image_data[i : i + self.chunk_size]
            yield chunk
            if delay_ms > 0:
                await asyncio.sleep(delay_ms)

    def stream_bytes_sync(self, image_data: bytes, delay_ms: float = 0.01):
        """
        Synchronous iterator version of stream_bytes.

        This can be used from blocking contexts to avoid asyncio.run errors
        when an event loop is already active.

        Yields:
            Chunks of image data as bytes.

        """

        import time

        for i in range(0, len(image_data), self.chunk_size):
            chunk = image_data[i : i + self.chunk_size]
            yield chunk
            if delay_ms > 0:
                time.sleep(delay_ms)

    async def stream_from_buffer(
        self, buffer: io.BytesIO, delay_ms: float = 0.01
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream image data from BytesIO buffer.

        Args:
            buffer: BytesIO buffer containing image data
            delay_ms: Delay between chunks in seconds

        Yields:
            Chunks of image data

        """
        buffer.seek(0)
        while True:
            chunk = buffer.read(self.chunk_size)
            if not chunk:
                break
            yield chunk
            if delay_ms > 0:
                await asyncio.sleep(delay_ms)

    def create_response(
        self,
        image_data: bytes,
        media_type: str = "image/png",
        filename: str | None = None,
    ) -> StreamingResponse:
        """
        Create FastAPI StreamingResponse for image.

        Args:
            image_data: Complete image data
            media_type: MIME type (default: "image/png")
            filename: Optional filename for Content-Disposition header

        Returns:
            FastAPI StreamingResponse

        Raises:
            ImportError: If FastAPI is not installed

        """
        if not HAS_FASTAPI:
            raise ImportError(
                "FastAPI is required for streaming responses. "
                "Install with: pip install household-mcp-server[streaming]"
            )

        headers = {}
        if filename:
            headers["Content-Disposition"] = f'inline; filename="{filename}"'

        # If an asyncio event loop is running, use the async generator.
        # Otherwise fall back to a synchronous iterator to avoid event loop
        # collisions.
        # fall back to the synchronous iterator. This avoids calling
        # ``asyncio.run`` from executing contexts that already have a loop.
        try:
            asyncio.get_running_loop()
            # Running inside an event loop — use async generator
            body = self.stream_bytes(image_data)
        except RuntimeError:
            # No running loop — use sync generator
            body = self.stream_bytes_sync(image_data)

        return StreamingResponse(body, media_type=media_type, headers=headers)

    @staticmethod
    def bytes_to_buffer(image_bytes: bytes) -> io.BytesIO:
        """
        Convert bytes to BytesIO buffer.

        Args:
            image_bytes: Image data as bytes

        Returns:
            BytesIO buffer positioned at start

        """
        buffer = io.BytesIO(image_bytes)
        buffer.seek(0)
        return buffer

    @staticmethod
    def buffer_to_bytes(buffer: io.BytesIO) -> bytes:
        """
        Extract bytes from BytesIO buffer.

        Args:
            buffer: BytesIO buffer

        Returns:
            Complete buffer content as bytes

        """
        position = buffer.tell()
        buffer.seek(0)
        data = buffer.read()
        buffer.seek(position)
        return data
