"""
Compatibility shim for household_mcp.server package.

This package replaces the legacy `household_mcp.server` module.
It re-exports symbols from `household_mcp.mcp_server` to maintain backward compatibility.
"""

from .. import mcp_server
from ..mcp_server import (
    _data_dir,
    _data_loader,
    _db_manager,
    _get_data_loader,
    app,
    create_http_app,
    list_tools,
    mcp,
)


# Unwrap tools to expose the underlying function for tests
def _unwrap_tool(tool):
    return getattr(tool, "fn", tool)


category_analysis = _unwrap_tool(mcp_server.category_analysis)
find_categories = _unwrap_tool(mcp_server.find_categories)
monthly_summary = _unwrap_tool(mcp_server.monthly_summary)

tool_confirm_duplicate = _unwrap_tool(mcp_server.tool_confirm_duplicate)
tool_detect_duplicates = _unwrap_tool(mcp_server.tool_detect_duplicates)
tool_get_duplicate_candidates = _unwrap_tool(mcp_server.tool_get_duplicate_candidates)
tool_get_duplicate_stats = _unwrap_tool(mcp_server.tool_get_duplicate_stats)
tool_restore_duplicate = _unwrap_tool(mcp_server.tool_restore_duplicate)

__all__ = [
    "_data_dir",
    "_data_loader",
    "_db_manager",
    "_get_data_loader",
    "app",
    "category_analysis",
    "create_http_app",
    "find_categories",
    "list_tools",
    "mcp",
    "monthly_summary",
    "tool_confirm_duplicate",
    "tool_detect_duplicates",
    "tool_get_duplicate_candidates",
    "tool_get_duplicate_stats",
    "tool_restore_duplicate",
]
