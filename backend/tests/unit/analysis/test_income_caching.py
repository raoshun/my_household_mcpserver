"""Tests for income_snapshots caching (TASK-2014, TASK-2015)."""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from household_mcp.analysis.income_analyzer import (
    IncomeAnalyzer,
    IncomeCategory,
)
from household_mcp.database.manager import DatabaseManager
from household_mcp.database.models import IncomeSnapshot
from household_mcp.dataloader import HouseholdDataLoader


@pytest.fixture
def db_manager(tmp_path):
    """Test database manager."""
    db_path = tmp_path / "test.db"
    db = DatabaseManager(str(db_path))
    db.initialize_database()
    return db


@pytest.fixture
def analyzer(db_manager):
    """Income analyzer with database."""
    data_loader = HouseholdDataLoader()
    return IncomeAnalyzer(data_loader, db_manager)


def test_cache_miss_and_save(analyzer, db_manager):
    """Test cache miss triggers CSV load and saves to cache."""
    # First call - cache miss
    summary1 = analyzer.get_monthly_summary(2024, 1)

    assert summary1.year == 2024
    assert summary1.month == 1
    assert isinstance(summary1.total_income, Decimal)

    # Verify snapshot saved to DB
    with db_manager.get_session() as session:
        snapshot = (
            session.query(IncomeSnapshot)
            .filter(IncomeSnapshot.snapshot_month == "2024-01")
            .first()
        )
        assert snapshot is not None
        assert snapshot.total_income == int(summary1.total_income)


def test_cache_hit(analyzer, db_manager):
    """Test cache hit returns cached data without CSV load."""
    # First call - populate cache
    summary1 = analyzer.get_monthly_summary(2024, 2)

    # Second call - should hit cache
    summary2 = analyzer.get_monthly_summary(2024, 2)

    assert summary1.total_income == summary2.total_income
    assert summary1.category_breakdown == summary2.category_breakdown

    # Verify only one DB record exists
    with db_manager.get_session() as session:
        count = (
            session.query(IncomeSnapshot)
            .filter(IncomeSnapshot.snapshot_month == "2024-02")
            .count()
        )
        assert count == 1


def test_cache_expiration(analyzer, db_manager):
    """Test cache expires after TTL (1 hour)."""
    # Populate cache
    summary1 = analyzer.get_monthly_summary(2024, 3)

    # Manually expire cache by setting updated_at to 2 hours ago
    with db_manager.get_session() as session:
        snapshot = (
            session.query(IncomeSnapshot)
            .filter(IncomeSnapshot.snapshot_month == "2024-03")
            .first()
        )
        snapshot.updated_at = datetime.now() - timedelta(hours=2)
        session.commit()

    # Next call should not use expired cache
    summary2 = analyzer.get_monthly_summary(2024, 3)

    # Should still return valid data (from CSV reload)
    assert summary2.year == 2024
    assert summary2.month == 3
    assert isinstance(summary2.total_income, Decimal)


def test_cache_update_on_recalculation(analyzer, db_manager):
    """Test cache updates when recalculated."""
    # Initial calculation
    summary1 = analyzer.get_monthly_summary(2024, 4)

    # Get initial updated_at
    with db_manager.get_session() as session:
        snapshot1 = (
            session.query(IncomeSnapshot)
            .filter(IncomeSnapshot.snapshot_month == "2024-04")
            .first()
        )
        updated_at_1 = snapshot1.updated_at

    # Force cache expiration
    with db_manager.get_session() as session:
        snapshot = (
            session.query(IncomeSnapshot)
            .filter(IncomeSnapshot.snapshot_month == "2024-04")
            .first()
        )
        snapshot.updated_at = datetime.now() - timedelta(hours=2)
        session.commit()

    # Recalculate
    summary2 = analyzer.get_monthly_summary(2024, 4)

    # Verify updated_at changed
    with db_manager.get_session() as session:
        snapshot2 = (
            session.query(IncomeSnapshot)
            .filter(IncomeSnapshot.snapshot_month == "2024-04")
            .first()
        )
        assert snapshot2.updated_at > updated_at_1


def test_without_database_manager():
    """Test analyzer works without database (no caching)."""
    data_loader = HouseholdDataLoader()
    analyzer = IncomeAnalyzer(data_loader, db_manager=None)

    # Should still work, just without caching
    summary = analyzer.get_monthly_summary(2024, 5)

    assert summary.year == 2024
    assert summary.month == 5
    assert isinstance(summary.total_income, Decimal)
