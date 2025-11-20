"""Core API routes for cache management and health checks."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)


def create_core_router(chart_cache: Any) -> APIRouter:
    """
    Create core API router.

    Args:
        chart_cache: Chart cache instance

    Returns:
        APIRouter with core endpoints

    """
    router = APIRouter(tags=["core"])

    @router.get("/api/cache/stats")
    async def get_cache_stats() -> dict[str, object]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics

        """
        return chart_cache.stats()

    @router.delete("/api/cache")
    async def clear_cache() -> dict[str, object]:
        """
        Clear all cached charts.

        Returns:
            Confirmation message

        """
        chart_cache.clear()
        logger.info("Cache cleared")
        return {"status": "success", "message": "Cache cleared"}

    @router.get("/health")
    async def health_check() -> dict[str, object]:
        """
        Health check endpoint.

        Returns:
            Health status

        """
        return {
            "status": "healthy",
            "service": "Household Budget Chart Server",
        }

    return router
