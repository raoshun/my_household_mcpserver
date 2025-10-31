"""Tests for duplicate detection MCP tools."""

import os
import tempfile

import pytest

from household_mcp.database import DatabaseManager
from household_mcp.tools import duplicate_tools


@pytest.fixture
def temp_db():
    """一時的なテストデータベースを作成."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_household.db")
        db_manager = DatabaseManager(db_path)
        db_manager.initialize_database()
        duplicate_tools.set_database_manager(db_manager)
        yield db_manager


def test_detect_duplicates_no_data(temp_db):
    """データがない場合の重複検出テスト."""
    result = duplicate_tools.detect_duplicates()
    assert result["success"] is True
    assert result["detected_count"] == 0


def test_get_duplicate_candidates_empty(temp_db):
    """候補がない場合のテスト."""
    result = duplicate_tools.get_duplicate_candidates(limit=10)
    assert result["success"] is True
    assert result["count"] == 0
    assert result["candidates"] == []


def test_get_duplicate_stats_empty(temp_db):
    """統計情報の取得テスト（データなし）."""
    result = duplicate_tools.get_duplicate_stats()
    assert result["success"] is True
    assert "stats" in result


def test_confirm_duplicate_invalid_id(temp_db):
    """存在しないチェックIDでの判定テスト."""
    result = duplicate_tools.confirm_duplicate(check_id=999, decision="duplicate")
    assert result["success"] is False


def test_restore_duplicate_invalid_id(temp_db):
    """存在しない取引IDでの復元テスト."""
    result = duplicate_tools.restore_duplicate(transaction_id=999)
    assert result["success"] is False
