"""Test asset export functionality."""

from datetime import datetime
from io import StringIO

import pytest

from household_mcp.assets.manager import AssetManager
from household_mcp.assets.models import AssetRecordRequest
from household_mcp.database.manager import DatabaseManager


@pytest.fixture
def temp_db_with_export_data(tmp_path):
    """Create temporary database with export test data."""
    db_path = str(tmp_path / "test_export.db")
    db = DatabaseManager(db_path=db_path)
    db.initialize_database()

    # Create diverse test data
    with db.session_scope() as session:
        manager = AssetManager(session)

        # January 2025 data
        manager.create_record(
            AssetRecordRequest(
                record_date=datetime(2025, 1, 15),
                asset_class_id=1,  # cash
                sub_asset_name="普通預金",
                amount=1000000,
                memo="給与振込",
            )
        )
        manager.create_record(
            AssetRecordRequest(
                record_date=datetime(2025, 1, 20),
                asset_class_id=2,  # stocks
                sub_asset_name="楽天VTI",
                amount=500000,
                memo="投資",
            )
        )

        # February 2025 data
        manager.create_record(
            AssetRecordRequest(
                record_date=datetime(2025, 2, 28),
                asset_class_id=1,  # cash
                sub_asset_name="普通預金",
                amount=1200000,
            )
        )
        manager.create_record(
            AssetRecordRequest(
                record_date=datetime(2025, 2, 28),
                asset_class_id=3,  # funds
                sub_asset_name="投信ABC",
                amount=300000,
            )
        )

    yield db
    db.close()


class TestAssetExport:
    """Test asset export methods."""

    def test_export_all_records_csv(self, temp_db_with_export_data):
        """Test exporting all records to CSV."""
        with temp_db_with_export_data.session_scope() as session:
            manager = AssetManager(session)
            csv_content = manager.export_records_csv()

            # Verify CSV content
            assert isinstance(csv_content, str)
            lines = csv_content.strip().split("\n")

            # Header + 4 records
            assert len(lines) >= 5

            # Check header
            header = lines[0]
            assert "record_date" in header
            assert "asset_class_name" in header
            assert "sub_asset_name" in header
            assert "amount" in header

    def test_export_by_asset_class(self, temp_db_with_export_data):
        """Test exporting records filtered by asset class."""
        with temp_db_with_export_data.session_scope() as session:
            manager = AssetManager(session)

            # Export only cash (class_id=1)
            csv_content = manager.export_records_csv(asset_class_id=1)

            lines = csv_content.strip().split("\n")
            # Header + 2 cash records
            assert len(lines) >= 3

            # All non-header lines should contain "現金" (cash class name)
            for line in lines[1:]:
                if line:
                    assert "現金" in line or "普通預金" in line

    def test_export_by_date_range(self, temp_db_with_export_data):
        """Test exporting records filtered by date range."""
        with temp_db_with_export_data.session_scope() as session:
            manager = AssetManager(session)

            # Export only February records
            csv_content = manager.export_records_csv(
                start_date=datetime(2025, 2, 1),
                end_date=datetime(2025, 2, 28),
            )

            lines = csv_content.strip().split("\n")
            # Header + 2 February records
            assert len(lines) >= 3

            # Check that all records are from February
            for line in lines[1:]:
                if line:
                    assert "2025-02" in line

    def test_export_by_class_and_date(self, temp_db_with_export_data):
        """Test exporting records with both class and date filters."""
        with temp_db_with_export_data.session_scope() as session:
            manager = AssetManager(session)

            # Export only February cash records
            csv_content = manager.export_records_csv(
                asset_class_id=1,
                start_date=datetime(2025, 2, 1),
                end_date=datetime(2025, 2, 28),
            )

            lines = csv_content.strip().split("\n")
            # Header + 1 February cash record
            assert len(lines) >= 2

            # Check content
            if len(lines) > 1:
                record_line = lines[1]
                assert "2025-02" in record_line
                assert "現金" in record_line or "普通預金" in record_line

    def test_export_empty_result(self, temp_db_with_export_data):
        """Test exporting when no records match filter."""
        with temp_db_with_export_data.session_scope() as session:
            manager = AssetManager(session)

            # Export from future date range
            csv_content = manager.export_records_csv(
                start_date=datetime(2025, 12, 1),
                end_date=datetime(2025, 12, 31),
            )

            lines = csv_content.strip().split("\n")
            # Only header, no records
            assert len(lines) == 1
            assert "record_date" in lines[0]

    def test_export_csv_formatting(self, temp_db_with_export_data):
        """Test CSV formatting correctness."""
        with temp_db_with_export_data.session_scope() as session:
            manager = AssetManager(session)
            csv_content = manager.export_records_csv()

            # Parse CSV
            from csv import DictReader

            reader = DictReader(StringIO(csv_content))
            records = list(reader)

            # Verify records have all required fields
            if records:
                first_record = records[0]
                assert "record_date" in first_record
                assert "asset_class_name" in first_record
                assert "sub_asset_name" in first_record
                assert "amount" in first_record

                # Verify data types
                assert first_record["record_date"]  # Should have a date
                assert first_record["asset_class_name"]  # Should have a class
                assert first_record["amount"]  # Should have an amount

    def test_export_multiclass_filtering(self, temp_db_with_export_data):
        """Test exporting records from different asset classes."""
        with temp_db_with_export_data.session_scope() as session:
            manager = AssetManager(session)

            # Get all records
            all_csv = manager.export_records_csv()
            all_lines = all_csv.strip().split("\n")

            # Get records for each class
            cash_csv = manager.export_records_csv(asset_class_id=1)
            cash_lines = cash_csv.strip().split("\n")

            stocks_csv = manager.export_records_csv(asset_class_id=2)
            stocks_lines = stocks_csv.strip().split("\n")

            funds_csv = manager.export_records_csv(asset_class_id=3)
            funds_lines = funds_csv.strip().split("\n")

            # Total records should be >= sum of class records
            # (accounting for header)
            total_filtered = (
                (len(cash_lines) - 1) + (len(stocks_lines) - 1) + (len(funds_lines) - 1)
            )
            total_all = len(all_lines) - 1

            assert total_filtered == total_all
