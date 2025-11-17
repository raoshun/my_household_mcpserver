"""
Database package for household MCP server.

This package supports optional installation. To avoid importing heavy
dependencies (like SQLAlchemy) when the "db" extra is not installed,
we lazily import symbols via ``__getattr__``.

Accessing database-related attributes without the "db" extra installed will
raise a clear ImportError explaining how to enable the feature.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "AssetClass",  # type: ignore[reportUnsupportedDunderAll]
    "AssetRecord",  # type: ignore[reportUnsupportedDunderAll]
    "Base",  # type: ignore[reportUnsupportedDunderAll]
    "Budget",  # type: ignore[reportUnsupportedDunderAll]
    "CSVImporter",  # type: ignore[reportUnsupportedDunderAll]
    "DatabaseManager",  # type: ignore[reportUnsupportedDunderAll]
    "DuplicateCheck",  # type: ignore[reportUnsupportedDunderAll]
    "FireAssetSnapshot",  # type: ignore[reportUnsupportedDunderAll]
    "Transaction",  # type: ignore[reportUnsupportedDunderAll]
    "get_active_transactions",  # type: ignore[reportUnsupportedDunderAll]
    "get_category_breakdown",  # type: ignore[reportUnsupportedDunderAll]
    "get_duplicate_impact_report",  # type: ignore[reportUnsupportedDunderAll]
    "get_monthly_summary",  # type: ignore[reportUnsupportedDunderAll]
]


def __getattr__(name: str) -> Any:  # pragma: no cover - import-time behavior
    try:
        if name == "DatabaseManager":
            from .manager import DatabaseManager as _DatabaseManager

            return _DatabaseManager
        if name in {"Base", "Budget", "DuplicateCheck", "Transaction"}:
            from .models import Base as _Base
            from .models import Budget as _Budget
            from .models import DuplicateCheck as _Dup
            from .models import Transaction as _Txn

            mapping = {
                "Base": _Base,
                "Budget": _Budget,
                "DuplicateCheck": _Dup,
                "Transaction": _Txn,
            }
            return mapping[name]
        if name in {"AssetClass", "AssetRecord", "FireAssetSnapshot"}:
            from .models import AssetClass as _AC
            from .models import AssetRecord as _AR
            from .models import FireAssetSnapshot as _FS

            mapping = {
                "AssetClass": _AC,
                "AssetRecord": _AR,
                "FireAssetSnapshot": _FS,
            }
            return mapping[name]
        if name == "CSVImporter":
            from .csv_importer import CSVImporter as _CSVImporter

            return _CSVImporter
        if name in {
            "get_active_transactions",
            "get_category_breakdown",
            "get_duplicate_impact_report",
            "get_monthly_summary",
        }:
            from . import query_helpers as _qh

            return getattr(_qh, name)
    except Exception as e:
        raise ImportError(
            "Database features are not available. Install with '.[db]' or '.[full]'"
        ) from e

    raise AttributeError(name)
