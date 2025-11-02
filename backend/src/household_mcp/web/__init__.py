"""
Web server package for household budget MCP server.

Provides FastAPI-based HTTP endpoints for chart streaming.
This package exposes a lazy import for the HTTP server to avoid
import-time side effects in environments without streaming extras.
"""

from __future__ import annotations

__all__ = ["create_http_app"]


def create_http_app(
    enable_cors: bool = True,
    allowed_origins: list[str] | None = None,
    cache_size: int = 50,
    cache_ttl: int = 3600,
) -> object:
    """
    Create FastAPI application for chart streaming (lazy import).

    This wrapper defers importing FastAPI and the HTTP server implementation
    until runtime, which keeps test environments lightweight and avoids
    coverage penalties when streaming extras are not installed.
    """
    from .http_server import create_http_app as _impl

    return _impl(
        enable_cors=enable_cors,
        allowed_origins=allowed_origins,
        cache_size=cache_size,
        cache_ttl=cache_ttl,
    )
