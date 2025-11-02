"""Compatibility shim for household_mcp.server package.

This package path conflicted with the existing module `household_mcp/server.py`.
To maintain backward compatibility (tests import `household_mcp.server` expecting
the module), we dynamically load the original module file and re-export its
public API. New HTTP server functionality is available from
`household_mcp.web.create_http_app`.
"""

from __future__ import annotations

import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

# Re-export the HTTP app factory from the non-conflicting web package
try:
    from household_mcp.web import create_http_app  # noqa: F401
except Exception:  # pragma: no cover - streaming extras may be absent
    # Keep import-time safe when FastAPI extras are not installed
    create_http_app = None  # type: ignore


def _load_legacy_server_module():
    """Load the original module file household_mcp/server.py by path.

    Returns:
        The loaded module object.
    """
    # This __init__.py is at .../household_mcp/server/__init__.py
    # The legacy module is at .../household_mcp/server.py (one level up)
    module_path = Path(__file__).resolve().parents[1] / "server.py"
    spec = spec_from_file_location("household_mcp._server_module", str(module_path))
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("Could not load legacy server module")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_server = _load_legacy_server_module()

# Re-export expected symbols for tests and external code
list_tools = getattr(_server, "list_tools", None)
list_tools_for_test = getattr(_server, "list_tools_for_test", None)
mcp = getattr(_server, "mcp", None)
app = getattr(_server, "app", None)
_db_manager = getattr(_server, "_db_manager", None)
_data_loader = getattr(_server, "_data_loader", None)

# Re-export _data_dir and _get_data_loader - keep references to original functions
# These will be accessed when tests mock household_mcp.server._data_dir or ._get_data_loader
_data_dir = getattr(_server, "_data_dir", None)
_get_data_loader = getattr(_server, "_get_data_loader", None)

# CRITICAL: Replace _server module's internal functions with our re-exported ones
# so that when category_analysis() calls _get_data_loader(), it uses the one from
# this module (which tests can mock), not the original _server module's version
setattr(_server, "_data_dir", _data_dir)
setattr(_server, "_get_data_loader", _get_data_loader)

# Re-export commonly used analysis tools (unwrap if decorated)
_monthly_summary = getattr(_server, "monthly_summary", None)
monthly_summary = (
    getattr(_monthly_summary, "fn", getattr(_monthly_summary, "func", _monthly_summary))
    if _monthly_summary is not None
    else None
)

_category_analysis = getattr(_server, "category_analysis", None)
category_analysis = (
    getattr(
        _category_analysis,
        "fn",
        getattr(_category_analysis, "func", _category_analysis),
    )
    if _category_analysis is not None
    else None
)

_find_categories = getattr(_server, "find_categories", None)
find_categories = (
    getattr(_find_categories, "fn", getattr(_find_categories, "func", _find_categories))
    if _find_categories is not None
    else None
)

# Re-export duplicate detection tools
# These are decorated with @mcp.tool, so we need to get the underlying function
_tool_detect_duplicates = getattr(_server, "tool_detect_duplicates", None)
_tool_get_duplicate_candidates = getattr(_server, "tool_get_duplicate_candidates", None)
_tool_confirm_duplicate = getattr(_server, "tool_confirm_duplicate", None)
_tool_restore_duplicate = getattr(_server, "tool_restore_duplicate", None)
_tool_get_duplicate_stats = getattr(_server, "tool_get_duplicate_stats", None)

# Extract the actual function from FunctionTool objects if needed
tool_detect_duplicates = (
    getattr(
        _tool_detect_duplicates,
        "fn",
        getattr(_tool_detect_duplicates, "func", _tool_detect_duplicates),
    )
    if _tool_detect_duplicates
    else None
)
tool_get_duplicate_candidates = (
    getattr(
        _tool_get_duplicate_candidates,
        "fn",
        getattr(_tool_get_duplicate_candidates, "func", _tool_get_duplicate_candidates),
    )
    if _tool_get_duplicate_candidates
    else None
)
tool_confirm_duplicate = (
    getattr(
        _tool_confirm_duplicate,
        "fn",
        getattr(_tool_confirm_duplicate, "func", _tool_confirm_duplicate),
    )
    if _tool_confirm_duplicate
    else None
)
tool_restore_duplicate = (
    getattr(
        _tool_restore_duplicate,
        "fn",
        getattr(_tool_restore_duplicate, "func", _tool_restore_duplicate),
    )
    if _tool_restore_duplicate
    else None
)
tool_get_duplicate_stats = (
    getattr(
        _tool_get_duplicate_stats,
        "fn",
        getattr(_tool_get_duplicate_stats, "func", _tool_get_duplicate_stats),
    )
    if _tool_get_duplicate_stats
    else None
)

__all__ = [
    "list_tools",
    "list_tools_for_test",
    "mcp",
    "app",
    "create_http_app",
    "_db_manager",
    "_data_loader",
    "_data_dir",
    "_get_data_loader",
    "monthly_summary",
    "category_analysis",
    "find_categories",
    "tool_detect_duplicates",
    "tool_get_duplicate_candidates",
    "tool_confirm_duplicate",
    "tool_restore_duplicate",
    "tool_get_duplicate_stats",
]
