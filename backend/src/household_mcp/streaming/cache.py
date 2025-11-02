"""
Image caching system for chart generation.

This module provides TTL-based caching for generated chart images.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

try:
    from cachetools import TTLCache

    HAS_CACHETOOLS = True
except ImportError:
    HAS_CACHETOOLS = False


class ChartCache:
    """
    TTL-based cache for chart images.

    Stores generated chart images in memory with automatic expiration.
    Uses parameter hashing for cache keys to ensure uniqueness.
    """

    def __init__(self, max_size: int = 50, ttl: int = 3600):
        """
        Initialize chart cache.

        Args:
            max_size: Maximum number of images to cache (default: 50)
            ttl: Time-to-live in seconds (default: 3600 = 1 hour)

        Raises:
            ImportError: If cachetools is not installed

        """
        if not HAS_CACHETOOLS:
            raise ImportError(
                "cachetools is required for ChartCache. "
                "Install with: pip install household-mcp-server[streaming]"
            )

        self.cache: TTLCache = TTLCache(maxsize=max_size, ttl=ttl)
        self._max_size = max_size
        self._ttl = ttl

    def get_key(self, params: dict[str, Any]) -> str:
        """
        Generate cache key from parameters.

        Args:
            params: Dictionary of chart generation parameters

        Returns:
            MD5 hash of sorted JSON parameters

        """
        # Sort keys for consistent hashing
        key_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode("utf-8")).hexdigest()

    def get(self, key: str) -> bytes | None:
        """
        Retrieve image from cache.

        Args:
            key: Cache key (typically from get_key())

        Returns:
            Image bytes if found, None otherwise

        """
        return self.cache.get(key)

    def set(self, key: str, image_data: bytes) -> None:
        """
        Store image in cache.

        Args:
            key: Cache key
            image_data: PNG/SVG image bytes

        """
        self.cache[key] = image_data

    def clear(self) -> None:
        """Clear all cached images."""
        self.cache.clear()

    def size(self) -> int:
        """Return current number of cached images."""
        return len(self.cache)

    @property
    def max_size(self) -> int:
        """Maximum cache size."""
        return self._max_size

    @property
    def ttl(self) -> int:
        """Time-to-live in seconds."""
        return self._ttl

    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with current_size, max_size, and ttl

        """
        return {
            "current_size": len(self.cache),
            "max_size": self._max_size,
            "ttl": self._ttl,
        }
