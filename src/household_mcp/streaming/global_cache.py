"""Global chart cache singleton.

Provides a process-wide ChartCache instance to share between
MCP tools and the HTTP server so that generated charts can be
served via `/api/charts/{chart_id}`.
"""

from __future__ import annotations

from typing import Optional

try:
    from .cache import ChartCache
except Exception:  # pragma: no cover - cachetools optional
    ChartCache = None  # type: ignore

# Global instance (may be None if cachetools not installed)
GLOBAL_CHART_CACHE: Optional["ChartCache"] = None


def ensure_global_cache(max_size: int = 50, ttl: int = 3600) -> Optional["ChartCache"]:
    """Ensure a global chart cache exists and return it.

    Returns None if streaming dependencies are missing.
    """
    global GLOBAL_CHART_CACHE
    if GLOBAL_CHART_CACHE is None and ChartCache is not None:
        try:
            GLOBAL_CHART_CACHE = ChartCache(max_size=max_size, ttl=ttl)
        except Exception:
            GLOBAL_CHART_CACHE = None
    return GLOBAL_CHART_CACHE


def get_global_cache() -> Optional["ChartCache"]:
    """Get the global chart cache instance (may be None)."""
    return GLOBAL_CHART_CACHE
