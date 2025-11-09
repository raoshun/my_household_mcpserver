"""
MCP Resource definitions for household budget data.

This module contains all @mcp.resource decorated functions
that were previously in server.py.
"""

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from household_mcp.database import DatabaseManager

from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.exceptions import DataSourceError
from household_mcp.tools.trend_tool import category_trend_summary

# Report tools availability flag
HAS_REPORT_TOOLS = True  # Assume available; gracefully degrade on import error

# Lazily initialized data loader
_data_loader: HouseholdDataLoader | None = None
_db_manager: "DatabaseManager | None" = None


def _data_dir() -> str:
    """
    Return the data directory path from env or default.

    HOUSEHOLD_DATA_DIR can be set in CI or runtime to point to fixtures.
    Defaults to "data" for local runs.
    """
    return os.getenv("HOUSEHOLD_DATA_DIR", "data")


def _get_data_loader() -> HouseholdDataLoader:
    global _data_loader
    if _data_loader is None:
        _data_loader = HouseholdDataLoader(src_dir=_data_dir())
    return _data_loader


def _get_db_manager() -> "DatabaseManager":
    """データベースマネージャーを取得（遅延初期化）."""
    global _db_manager
    if _db_manager is None:
        db_path = os.path.join(_data_dir(), "household.db")
        try:
            from household_mcp.database import DatabaseManager
        except Exception as e:
            raise ImportError(
                "Database features are not available. Install with '.[db]' or '.[full]'"
            ) from e

        _db_manager = DatabaseManager(db_path)
        _db_manager.initialize_database()
    return _db_manager


def get_category_hierarchy() -> dict[str, list[str]]:
    """
    家計簿のカテゴリの階層構造を取得する関数。

    Returns:
        dict[str, list[str]]: カテゴリの階層構造(大項目: [中項目1, 中項目2, ...])を表す辞書

    """
    try:
        result = _get_data_loader().category_hierarchy(year=2025, month=7)
        return dict(result)  # 明示的キャスト
    except DataSourceError:
        # データ未配置時は空で返す
        return {}


def get_available_months() -> list[dict[str, int]]:
    """利用可能な月のリストを CSV ファイルから動的に検出して返す。"""
    try:
        months = list(_get_data_loader().iter_available_months())
        return [{"year": year, "month": month} for year, month in months]
    except DataSourceError:
        return []


def get_household_categories() -> dict[str, list[str]]:
    """
    家計簿のカテゴリ一覧を取得する関数。

    Returns:
        dict[str, list[str]]: カテゴリの階層構造(大項目: [中項目1, 中項目2, ...])を表す辞書

    """
    try:
        result = _get_data_loader().category_hierarchy(year=2025, month=7)
        return dict(result)
    except DataSourceError:
        return {}


def get_category_trend_summary() -> dict[str, Any]:
    """トレンド分析用のカテゴリ集計結果を返す。"""
    try:
        result = category_trend_summary(src_dir=_data_dir())
        return dict(result)
    except DataSourceError:
        return {"summary": {}}


def get_transactions() -> dict[str, Any]:
    """Get transactions for the latest available month from database."""
    if not HAS_REPORT_TOOLS:
        return {"error": "Report tools not available"}
    try:
        from household_mcp.database.models import Transaction
        from household_mcp.tools.report_tools import export_transactions

        db_manager = _get_db_manager()
        session = db_manager.get_session()
        try:
            # Get latest month
            query = (
                session.query(Transaction.date)
                .order_by(Transaction.date.desc())
                .first()
            )
            if not query:
                return {"transactions": [], "period": "No data"}
            latest_date = query[0]
            year, month = latest_date.year, latest_date.month
            # Use export_transactions to get month data
            result = export_transactions(year, month, format="json")
            return {"transactions": result}
        finally:
            session.close()
    except Exception as e:
        return {"error": f"Failed to get transactions: {e!s}"}


def get_monthly_summary_resource() -> dict[str, Any]:
    """Get monthly summary report for latest month."""
    if not HAS_REPORT_TOOLS:
        return {"error": "Report tools not available"}
    try:
        from household_mcp.database.models import Transaction
        from household_mcp.tools.report_tools import generate_report

        db_manager = _get_db_manager()
        session = db_manager.get_session()
        try:
            # Get latest month
            query = (
                session.query(Transaction.date)
                .order_by(Transaction.date.desc())
                .first()
            )
            if not query:
                return {"summary": None}
            latest_date = query[0]
            year, month = latest_date.year, latest_date.month
            # Use generate_report to get summary
            result = generate_report(year, month, "summary")
            return {"summary": result}
        finally:
            session.close()
    except Exception as e:
        return {"error": f"Failed to get summary: {e!s}"}


def get_budget_status_resource() -> dict[str, Any]:
    """Get budget status (actual vs budget) for latest month."""
    if not HAS_REPORT_TOOLS:
        return {"error": "Report tools not available"}
    try:
        from household_mcp.database.models import Transaction
        from household_mcp.tools.report_tools import generate_report

        db_manager = _get_db_manager()
        session = db_manager.get_session()
        try:
            # Get latest month
            query = (
                session.query(Transaction.date)
                .order_by(Transaction.date.desc())
                .first()
            )
            if not query:
                return {"budget_status": None}
            latest_date = query[0]
            year, month = latest_date.year, latest_date.month
            # Use generate_report to get category breakdown
            result = generate_report(year, month, "category")
            return {"budget_status": result}
        finally:
            session.close()
    except Exception as e:
        return {"error": f"Failed to get budget status: {e!s}"}
