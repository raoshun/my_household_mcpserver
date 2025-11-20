"""Duplicate detection and management API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)


def create_duplicate_router() -> APIRouter:
    """
    Create duplicate detection API router.

    Returns:
        APIRouter with duplicate endpoints

    """
    router = APIRouter(prefix="/api/duplicates", tags=["duplicates"])

    @router.post("/detect")
    async def detect_duplicates(
        date_tolerance_days: int = Query(0, description="Date tolerance in days"),
        amount_tolerance_abs: float = Query(
            0.0, description="Absolute amount tolerance"
        ),
        amount_tolerance_pct: float = Query(
            0.0, description="Percentage amount tolerance"
        ),
    ) -> dict[str, Any]:
        """
        Detect duplicate transactions.

        Args:
            date_tolerance_days: Date tolerance in days (default: 0)
            amount_tolerance_abs: Absolute amount tolerance (default: 0.0)
            amount_tolerance_pct: Percentage amount tolerance (default: 0.0)

        Returns:
            Detection results with count

        """
        try:
            from household_mcp.tools import duplicate_tools

            result = duplicate_tools.detect_duplicates(
                date_tolerance_days=date_tolerance_days,
                amount_tolerance_abs=amount_tolerance_abs,
                amount_tolerance_pct=amount_tolerance_pct,
            )
            return result
        except Exception as e:
            logger.exception(f"Error detecting duplicates: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/candidates")
    async def get_duplicate_candidates(
        limit: int = Query(10, description="Maximum number of candidates to return"),
    ) -> dict[str, Any]:
        """
        Get list of duplicate candidates.

        Args:
            limit: Maximum number of candidates to return (default: 10)

        Returns:
            List of duplicate candidate pairs

        """
        try:
            from household_mcp.tools import duplicate_tools

            result = duplicate_tools.get_duplicate_candidates(limit=limit)
            return result
        except Exception as e:
            logger.exception(f"Error getting duplicate candidates: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{check_id}")
    async def get_duplicate_detail(
        check_id: int,
    ) -> dict[str, Any]:
        """
        Get details of a duplicate candidate.

        Args:
            check_id: Duplicate check ID

        Returns:
            Detailed information about the duplicate candidate

        """
        try:
            from household_mcp.tools import duplicate_tools

            result = duplicate_tools.get_duplicate_candidate_detail(check_id=check_id)
            return result
        except Exception as e:
            logger.exception(f"Error getting duplicate detail: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/{check_id}/confirm")
    async def confirm_duplicate(
        check_id: int,
        decision: str = Query(
            ..., description="Decision: duplicate, not_duplicate, or skip"
        ),
    ) -> dict[str, Any]:
        """
        Confirm duplicate decision.

        Args:
            check_id: Duplicate check ID
            decision: Decision (duplicate, not_duplicate, or skip)

        Returns:
            Confirmation result

        """
        if decision not in ["duplicate", "not_duplicate", "skip"]:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid decision. Must be 'duplicate', 'not_duplicate', or 'skip'"
                ),
            )

        try:
            from household_mcp.tools import duplicate_tools

            result = duplicate_tools.confirm_duplicate(
                check_id=check_id,
                decision=decision,
            )
            return result
        except Exception as e:
            logger.exception(f"Error confirming duplicate: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/restore/{transaction_id}")
    async def restore_duplicate(
        transaction_id: int,
    ) -> dict[str, Any]:
        """
        Restore a transaction marked as duplicate.

        Args:
            transaction_id: Transaction ID to restore

        Returns:
            Restoration result

        """
        try:
            from household_mcp.tools import duplicate_tools

            result = duplicate_tools.restore_duplicate(transaction_id=transaction_id)
            return result
        except Exception as e:
            logger.exception(f"Error restoring duplicate: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/stats")
    async def get_duplicate_stats() -> dict[str, Any]:
        """
        Get duplicate detection statistics.

        Returns:
            Statistics about detected duplicates

        """
        try:
            from household_mcp.tools import duplicate_tools

            result = duplicate_tools.get_duplicate_stats()
            return result
        except Exception as e:
            logger.exception(f"Error getting duplicate stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
