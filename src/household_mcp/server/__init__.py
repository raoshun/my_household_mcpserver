"""Compatibility shim for household_mcp.server package.

This package path conflicted with the existing module `household_mcp/server.py`.
To maintain backward compatibility (tests import `household_mcp.server` expecting
the module), we dynamically load the original module file and re-export its
public API. New HTTP server functionality is available from
`household_mcp.web.create_http_app`.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

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
mcp = getattr(_server, "mcp", None)
app = getattr(_server, "app", None)

__all__ = ["list_tools", "mcp", "app", "create_http_app"]
