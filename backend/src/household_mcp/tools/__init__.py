"""MCP tool helpers for the household server."""

from .duplicate_tools import (
    confirm_duplicate,
    detect_duplicates,
    get_duplicate_candidate_detail,
    get_duplicate_candidates,
    get_duplicate_stats,
    restore_duplicate,
    set_database_manager,
)
from .trend_tool import category_trend_summary, get_category_trend

__all__ = [
    "category_trend_summary",
    "confirm_duplicate",
    "detect_duplicates",
    "get_category_trend",
    "get_duplicate_candidate_detail",
    "get_duplicate_candidates",
    "get_duplicate_stats",
    "restore_duplicate",
    "set_database_manager",
]
