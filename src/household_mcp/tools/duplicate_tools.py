"""Duplicate detection MCP tools for household MCP server."""

from typing import Any, Dict, Literal

from household_mcp.database import DatabaseManager
from household_mcp.duplicate import DetectionOptions, DuplicateService

# Global database manager instance
_db_manager: DatabaseManager | None = None


def set_database_manager(db_manager: DatabaseManager) -> None:
    """Set the database manager for duplicate tools."""
    global _db_manager  # noqa: PLW0603
    _db_manager = db_manager


def _get_db_manager() -> DatabaseManager:
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
    try:
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
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}


def get_duplicate_candidates(limit: int = 10) -> Dict[str, Any]:
    """未判定の重複候補を取得."""
    try:
        db_manager = _get_db_manager()
        with db_manager.session_scope() as session:
            service = DuplicateService(session)
            candidates = service.get_pending_candidates(limit)
            return {"success": True, "count": len(candidates), "candidates": candidates}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}


def get_duplicate_candidate_detail(check_id: int) -> Dict[str, Any]:
    """重複候補の詳細を取得."""
    try:
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
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}


def confirm_duplicate(
    check_id: int, decision: Literal["duplicate", "not_duplicate", "skip"]
) -> Dict[str, Any]:
    """重複判定結果を記録."""
    try:
        db_manager = _get_db_manager()
        with db_manager.session_scope() as session:
            service = DuplicateService(session)
            result: Dict[str, Any] = service.confirm_duplicate(check_id, decision)
            return result
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}


def restore_duplicate(transaction_id: int) -> Dict[str, Any]:
    """誤って重複とマークした取引を復元."""
    try:
        db_manager = _get_db_manager()
        with db_manager.session_scope() as session:
            service = DuplicateService(session)
            result: Dict[str, Any] = service.restore_duplicate(transaction_id)
            return result
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}


def get_duplicate_stats() -> Dict[str, Any]:
    """重複検出の統計情報を取得."""
    try:
        db_manager = _get_db_manager()
        with db_manager.session_scope() as session:
            service = DuplicateService(session)
            stats = service.get_stats()
            return {"success": True, "stats": stats}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": str(e)}
