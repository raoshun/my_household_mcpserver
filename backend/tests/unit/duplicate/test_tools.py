"""Unit tests for duplicate detection MCP tools."""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, Mock, patch

import pytest

from household_mcp.database.models import Transaction
from household_mcp.tools import duplicate_tools


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    manager = Mock()
    manager.session_scope = MagicMock()
    return manager


@pytest.fixture(autouse=True)
def setup_db_manager(mock_db_manager):
    """Setup database manager for tests."""
    duplicate_tools.set_database_manager(mock_db_manager)
    yield
    duplicate_tools._db_manager = None


def test_detect_duplicates_success():
    """Test detect_duplicates returns success."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.detect_and_save_candidates.return_value = 5

        result = duplicate_tools.detect_duplicates(
            date_tolerance_days=1,
            amount_tolerance_abs=100.0,
            amount_tolerance_pct=5.0,
            min_similarity_score=0.9,
        )

        assert result["success"] is True
        assert result["detected_count"] == 5
        assert "5件の重複候補を検出しました" in result["message"]


def test_detect_duplicates_error():
    """Test detect_duplicates handles errors."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        MockService.side_effect = Exception("Database error")

        result = duplicate_tools.detect_duplicates()

        assert result["success"] is False
        assert "error" in result


def test_get_duplicate_candidates_success():
    """Test get_duplicate_candidates returns candidates."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_pending_candidates.return_value = [
            {
                "check_id": 1,
                "transaction_1": {"id": 1, "amount": -5000.0},
                "transaction_2": {"id": 2, "amount": -5000.0},
                "similarity_score": 1.0,
            }
        ]

        result = duplicate_tools.get_duplicate_candidates(limit=10)

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["candidates"]) == 1


def test_get_duplicate_candidates_empty():
    """Test get_duplicate_candidates with no candidates."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_pending_candidates.return_value = []

        result = duplicate_tools.get_duplicate_candidates()

        assert result["success"] is True
        assert result["count"] == 0
        assert result["candidates"] == []


def test_get_duplicate_candidate_detail_success():
    """Test get_duplicate_candidate_detail returns detail."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_candidate_detail.return_value = {
            "check_id": 1,
            "transaction_1": {"id": 1},
            "transaction_2": {"id": 2},
            "similarity_score": 1.0,
        }

        result = duplicate_tools.get_duplicate_candidate_detail(check_id=1)

        assert result["success"] is True
        assert "detail" in result
        assert result["detail"]["check_id"] == 1


def test_get_duplicate_candidate_detail_not_found():
    """Test get_duplicate_candidate_detail when not found."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_candidate_detail.return_value = None

        result = duplicate_tools.get_duplicate_candidate_detail(check_id=999)

        assert result["success"] is False
        assert "見つかりません" in result["message"]


def test_confirm_duplicate_success():
    """Test confirm_duplicate returns success."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.confirm_duplicate.return_value = {
            "success": True,
            "message": "重複として記録しました",
            "marked_transaction_id": 2,
        }

        result = duplicate_tools.confirm_duplicate(check_id=1, decision="duplicate")

        assert result["success"] is True
        assert "marked_transaction_id" in result


def test_confirm_duplicate_not_duplicate():
    """Test confirm_duplicate with not_duplicate decision."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.confirm_duplicate.return_value = {
            "success": True,
            "message": "重複ではないと記録しました",
        }

        result = duplicate_tools.confirm_duplicate(check_id=1, decision="not_duplicate")

        assert result["success"] is True


def test_confirm_duplicate_skip():
    """Test confirm_duplicate with skip decision."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.confirm_duplicate.return_value = {
            "success": True,
            "message": "保留として記録しました",
        }

        result = duplicate_tools.confirm_duplicate(check_id=1, decision="skip")

        assert result["success"] is True


def test_restore_duplicate_success():
    """Test restore_duplicate returns success."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.restore_duplicate.return_value = {
            "success": True,
            "message": "取引ID 2 を復元しました。",
        }

        result = duplicate_tools.restore_duplicate(transaction_id=2)

        assert result["success"] is True


def test_restore_duplicate_not_marked():
    """Test restore_duplicate when transaction not marked."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.restore_duplicate.return_value = {
            "success": False,
            "message": "マークされていません",
        }

        result = duplicate_tools.restore_duplicate(transaction_id=999)

        assert result["success"] is False


def test_get_duplicate_stats_success():
    """Test get_duplicate_stats returns statistics."""
    with patch("household_mcp.tools.duplicate_tools.DuplicateService") as MockService:
        mock_service = MockService.return_value
        mock_service.get_stats.return_value = {
            "total_transactions": 100,
            "duplicate_transactions": 5,
            "total_checks": 10,
            "pending_checks": 3,
        }

        result = duplicate_tools.get_duplicate_stats()

        assert result["success"] is True
        assert "stats" in result
        assert result["stats"]["total_transactions"] == 100


def test_db_manager_not_initialized():
    """Test error when database manager not initialized."""
    duplicate_tools._db_manager = None

    result = duplicate_tools.detect_duplicates()

    assert result["success"] is False
    assert "error" in result
