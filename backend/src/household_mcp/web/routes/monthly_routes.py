"""Monthly summary and data API routes."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)


def create_monthly_router() -> APIRouter:
    """
    Create monthly data API router.

    Returns:
        APIRouter with monthly endpoints

    """
    router = APIRouter(prefix="/api", tags=["monthly"])

    @router.get("/monthly")
    async def get_monthly_data(
        year: int = Query(..., description="Year"),
        month: int = Query(..., description="Month (1-12)"),
        output_format: str = Query("json", description="Output format: json or image"),
        graph_type: str = Query("pie", description="Graph type: pie, bar, line, area"),
        image_size: str = Query("800x600", description="Image size (WxH)"),
    ) -> dict[str, Any]:
        """
        Get monthly household data.

        Args:
            year: Year
            month: Month (1-12)
            output_format: Output format (json or image)
            graph_type: Graph type (pie, bar, line, area)
            image_size: Image size (WxH)

        Returns:
            Monthly data or image information

        """
        try:
            from household_mcp.dataloader import HouseholdDataLoader
            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary

            data_dir = os.getenv("HOUSEHOLD_DATA_DIR", "data")

            if output_format == "image":
                # Generate image
                result = enhanced_monthly_summary(
                    year=year,
                    month=month,
                    output_format="image",
                    graph_type=graph_type,
                    image_size=image_size,
                )
                return result
            else:
                # Return JSON data
                loader = HouseholdDataLoader(src_dir=data_dir)
                df = loader.load_month(year, month)
                records = df.to_dict(orient="records")
                return {
                    "success": True,
                    "year": year,
                    "month": month,
                    "data": records,
                    "count": len(records),
                }
        except Exception as e:
            logger.exception(f"Error getting monthly data: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/available-months")
    async def get_available_months() -> dict[str, Any]:
        """
        Get list of available months.

        Returns:
            List of available year-month combinations

        """
        try:
            from household_mcp.dataloader import HouseholdDataLoader

            data_dir = os.getenv("HOUSEHOLD_DATA_DIR", "data")
            loader = HouseholdDataLoader(src_dir=data_dir)
            months = [
                {"year": year, "month": month}
                for year, month in loader.iter_available_months()
            ]
            return {"success": True, "months": months}
        except Exception as e:
            logger.exception(f"Error getting available months: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/category-hierarchy")
    async def get_category_hierarchy(
        year: int = Query(2025, description="Year"),
        month: int = Query(1, description="Month"),
    ) -> dict[str, Any]:
        """
        Get category hierarchy.

        Args:
            year: Year
            month: Month

        Returns:
            Category hierarchy

        """
        try:
            from household_mcp.dataloader import HouseholdDataLoader

            data_dir = os.getenv("HOUSEHOLD_DATA_DIR", "data")
            loader = HouseholdDataLoader(src_dir=data_dir)
            hierarchy = loader.category_hierarchy(year=year, month=month)
            return {"success": True, "hierarchy": dict(hierarchy)}
        except Exception as e:
            logger.exception(f"Error getting category hierarchy: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
