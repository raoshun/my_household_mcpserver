"""Test asset aggregation methods."""

from datetime import datetime

import pytest

from household_mcp.assets.manager import AssetManager
from household_mcp.assets.models import AssetRecordRequest
from household_mcp.database.manager import DatabaseManager


@pytest.fixture
def temp_db_with_records(tmp_path):
    """Create temporary database with test records."""
    db_path = str(tmp_path / "test_agg.db")
    db = DatabaseManager(db_path=db_path)
    db.initialize_database()

    # Create test data
    with db.session_scope() as session:
        manager = AssetManager(session)

        # Add records for January 2025
        manager.create_record(
            AssetRecordRequest(
                record_date=datetime(2025, 1, 31),
                asset_class_id=1,  # cash
                sub_asset_name="普通預金",
                amount=1000000,
            )
        )
        manager.create_record(
            AssetRecordRequest(
                record_date=datetime(2025, 1, 31),
                asset_class_id=2,  # stocks
                sub_asset_name="楽天VTI",
                amount=500000,
            )
        )
        manager.create_record(
            AssetRecordRequest(
                record_date=datetime(2025, 1, 31),
                asset_class_id=3,  # funds
                sub_asset_name="投信ABC",
                amount=300000,
            )
        )

    yield db
    db.close()


class TestAssetAggregation:
    """Test asset aggregation methods."""

    def test_get_summary(self, temp_db_with_records):
        """Test getting asset summary."""
        with temp_db_with_records.session_scope() as session:
            manager = AssetManager(session)
            summary = manager.get_summary(2025, 1)

            assert summary["year"] == 2025
            assert summary["month"] == 1
            assert summary["date"] == "2025-01-31"
            assert "summary" in summary
            assert len(summary["summary"]) == 3
            assert summary["total_balance"] == 1800000

    def test_get_summary_class_breakdown(self, temp_db_with_records):
        """Test asset class breakdown in summary."""
        with temp_db_with_records.session_scope() as session:
            manager = AssetManager(session)
            summary = manager.get_summary(2025, 1)

            # Create a map of class IDs to balances
            balance_map = {
                item["asset_class_id"]: item["balance"] for item in summary["summary"]
            }

            assert balance_map[1] == 1000000  # cash
            assert balance_map[2] == 500000  # stocks
            assert balance_map[3] == 300000  # funds

    def test_get_allocation(self, temp_db_with_records):
        """Test getting asset allocation."""
        with temp_db_with_records.session_scope() as session:
            manager = AssetManager(session)
            allocation = manager.get_allocation(2025, 1)

            assert allocation["year"] == 2025
            assert allocation["month"] == 1
            assert allocation["date"] == "2025-01-31"
            assert allocation["total_assets"] == 1800000
            assert "allocations" in allocation
            assert len(allocation["allocations"]) == 3

    def test_get_allocation_percentages(self, temp_db_with_records):
        """Test allocation percentages."""
        with temp_db_with_records.session_scope() as session:
            manager = AssetManager(session)
            allocation = manager.get_allocation(2025, 1)

            # Create a map of class IDs to percentages
            pct_map = {
                item["asset_class_id"]: item["percentage"]
                for item in allocation["allocations"]
            }

            # Check percentages (with rounding)
            assert pct_map[1] == 55.56  # 1000000/1800000 * 100 ≈ 55.56
            assert pct_map[2] == 27.78  # 500000/1800000 * 100 ≈ 27.78
            assert pct_map[3] == 16.67  # 300000/1800000 * 100 ≈ 16.67

    def test_get_summary_no_records(self, tmp_path):
        """Test summary with no records."""
        db_path = str(tmp_path / "test_empty.db")
        db = DatabaseManager(db_path=db_path)
        db.initialize_database()

        try:
            with db.session_scope() as session:
                manager = AssetManager(session)
                summary = manager.get_summary(2025, 1)

                assert summary["year"] == 2025
                assert summary["month"] == 1
                assert summary["total_balance"] == 0
                assert len(summary["summary"]) == 0
        finally:
            db.close()

    def test_get_allocation_no_records(self, tmp_path):
        """Test allocation with no records."""
        db_path = str(tmp_path / "test_empty2.db")
        db = DatabaseManager(db_path=db_path)
        db.initialize_database()

        try:
            with db.session_scope() as session:
                manager = AssetManager(session)
                allocation = manager.get_allocation(2025, 1)

                assert allocation["year"] == 2025
                assert allocation["month"] == 1
                assert allocation["total_assets"] == 0
                assert len(allocation["allocations"]) == 0
        finally:
            db.close()

    def test_summary_february(self, temp_db_with_records):
        """Test summary for February (carries forward January records)."""
        with temp_db_with_records.session_scope() as session:
            manager = AssetManager(session)
            summary = manager.get_summary(2025, 2)

            # February should carry forward January records
            # (since they're still valid at end of Feb)
            assert summary["year"] == 2025
            assert summary["month"] == 2
            assert summary["date"] == "2025-02-28"
            # Should have the same records as January
            assert summary["total_balance"] == 1800000
            assert len(summary["summary"]) == 3
