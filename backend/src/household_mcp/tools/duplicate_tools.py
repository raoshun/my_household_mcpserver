"""Duplicate detection MCP tools for household MCP server.

This module is importable even when the optional "db" extras are not installed.
We avoid importing heavy database dependencies at import time by using a
lightweight protocol for typing and expecting the server to inject a concrete
database manager via ``set_database_manager``.
"""

from typing import Any, ContextManager, Dict, Literal, Protocol, runtime_checkable

try:
    # Optional db dependencies; may not be installed in minimal environments
    from household_mcp.duplicate import DetectionOptions, DuplicateService

    _HAS_DB_DEPS = True
except Exception:  # noqa: BLE001
    DetectionOptions = None
    DuplicateService = None
    _HAS_DB_DEPS = False


@runtime_checkable
class _DBManagerProto(Protocol):
    """Minimal protocol for the database manager used by duplicate tools."""

    def session_scope(self) -> ContextManager[Any]:  # pragma: no cover
        ...


# Global database manager instance
_db_manager: _DBManagerProto | None = None


def set_database_manager(db_manager: _DBManagerProto) -> None:
    """Set the database manager for duplicate tools."""
    global _db_manager  # noqa: PLW0603
    _db_manager = db_manager


def _get_db_manager() -> _DBManagerProto:
    """Get the database manager instance."""
    if _db_manager is None:
        raise RuntimeError(
            "Database manager not initialized. Call set_database_manager first."
        )
    return _db_manager


def detect_duplicates(
    date_tolerance_days: int = 0,
    amount_tolerance_abs: float = 0.0,
    amount_tolerance_pct: float = 0.0,
    min_similarity_score: float = 0.8,
) -> Dict[str, Any]:
    """重複候補を検出してデータベースに保存."""
    if not _HAS_DB_DEPS or DuplicateService is None or DetectionOptions is None:
        return {
            "success": False,
            "error": "Database features are not available. Install with '.[db]' or '.[full]'.",
        }
    db_manager = _get_db_manager()
    with db_manager.session_scope() as session:
        options = DetectionOptions(
            date_tolerance_days=date_tolerance_days,
            amount_tolerance_abs=amount_tolerance_abs,
            amount_tolerance_pct=amount_tolerance_pct,
            min_similarity_score=min_similarity_score,
        )
        service = DuplicateService(session)
        count = service.detect_and_save_candidates(options)
        return {
            "success": True,
            "detected_count": count,
            "message": f"{count}件の重複候補を検出しました",
        }


def get_duplicate_candidates(limit: int = 10) -> Dict[str, Any]:
    """未判定の重複候補を取得."""
    if not _HAS_DB_DEPS or DuplicateService is None:
        return {
            "success": False,
            "error": "Database features are not available. Install with '.[db]' or '.[full]'.",
        }
    db_manager = _get_db_manager()
    with db_manager.session_scope() as session:
        service = DuplicateService(session)
        candidates = service.get_pending_candidates(limit)
        return {"success": True, "count": len(candidates), "candidates": candidates}


def get_duplicate_candidate_detail(check_id: int) -> Dict[str, Any]:
    """重複候補の詳細を取得."""
    if not _HAS_DB_DEPS or DuplicateService is None:
        return {
            "success": False,
            "message": "Database features are not available. Install with '.[db]' or '.[full]'.",
        }
    db_manager = _get_db_manager()
    with db_manager.session_scope() as session:
        service = DuplicateService(session)
        detail = service.get_candidate_detail(check_id)
        if detail is None:
            return {
                "success": False,
                "message": f"チェックID {check_id} が見つかりません",
            }
        return {"success": True, "detail": detail}


def confirm_duplicate(
    check_id: int, decision: Literal["duplicate", "not_duplicate", "skip"]
) -> Dict[str, Any]:
    """重複判定結果を記録."""
    if not _HAS_DB_DEPS or DuplicateService is None:
        return {
            "success": False,
            "error": "Database features are not available. Install with '.[db]' or '.[full]'.",
        }
    db_manager = _get_db_manager()
    with db_manager.session_scope() as session:
        service = DuplicateService(session)
        result: Dict[str, Any] = service.confirm_duplicate(check_id, decision)
        return result


def restore_duplicate(transaction_id: int) -> Dict[str, Any]:
    """誤って重複とマークした取引を復元."""
    if not _HAS_DB_DEPS or DuplicateService is None:
        return {
            "success": False,
            "error": "Database features are not available. Install with '.[db]' or '.[full]'.",
        }
    db_manager = _get_db_manager()
    with db_manager.session_scope() as session:
        service = DuplicateService(session)
        result: Dict[str, Any] = service.restore_duplicate(transaction_id)
        return result


def get_duplicate_stats() -> Dict[str, Any]:
    """重複検出の統計情報を取得."""
    if not _HAS_DB_DEPS or DuplicateService is None:
        return {
            "success": False,
            "error": "Database features are not available. Install with '.[db]' or '.[full]'.",
        }
    db_manager = _get_db_manager()
    with db_manager.session_scope() as session:
        service = DuplicateService(session)
        stats = service.get_stats()
        return {"success": True, "stats": stats}
