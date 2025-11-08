"""Chart API routes for streaming and managing cached charts."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)


def create_chart_router(chart_cache: Any, image_streamer: Any) -> APIRouter:
    """
    Create chart API router.

    Args:
        chart_cache: Chart cache instance
        image_streamer: Image streamer instance

    Returns:
        APIRouter with chart endpoints

    """
    router = APIRouter(prefix="/api/charts", tags=["charts"])

    @router.get("/{chart_id}")
    async def stream_chart(
        chart_id: str,
    ) -> StreamingResponse:  # type: ignore[no-untyped-def]
        """
        Stream a generated chart image.

        Args:
            chart_id: Unique identifier for the chart (cache key)

        Returns:
            StreamingResponse with image data

        Raises:
            HTTPException: If chart not found in cache (404)

        """
        logger.info(f"Request for chart: {chart_id}")

        # Retrieve from cache
        image_data = chart_cache.get(chart_id)
        if image_data is None:
            logger.warning(f"Chart not found: {chart_id}")
            raise HTTPException(status_code=404, detail=f"Chart '{chart_id}' not found")

        # Stream the image
        logger.info(f"Streaming chart: {chart_id} ({len(image_data)} bytes)")
        return image_streamer.create_response(
            image_data,
            media_type="image/png",
            filename=f"chart_{chart_id}.png",
        )

    @router.get("/{chart_id}/info")
    async def get_chart_info(
        chart_id: str,
    ) -> dict[str, object]:  # type: ignore[no-untyped-def]
        """
        Get information about a cached chart.

        Args:
            chart_id: Unique identifier for the chart

        Returns:
            Dictionary with chart metadata

        Raises:
            HTTPException: If chart not found in cache (404)

        """
        image_data = chart_cache.get(chart_id)
        if image_data is None:
            raise HTTPException(status_code=404, detail=f"Chart '{chart_id}' not found")

        return {
            "chart_id": chart_id,
            "size_bytes": len(image_data),
            "media_type": "image/png",
        }

    return router
