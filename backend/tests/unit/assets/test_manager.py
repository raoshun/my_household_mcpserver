"""Test asset manager."""

from datetime import datetime

import pytest

from household_mcp.assets.manager import AssetManager
from household_mcp.assets.models import AssetRecordRequest
from household_mcp.database.manager import DatabaseManager


@pytest.fixture
def temp_db_with_manager(tmp_path):
    """Create a temporary database with manager."""
    db_path = str(tmp_path / "test_assets.db")
    db = DatabaseManager(db_path=db_path)
    db.initialize_database()
    yield db
    db.close()


class TestAssetManager:
    """Test AssetManager class."""

    def test_create_record(self, temp_db_with_manager):
        """Test creating an asset record."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)

            request = AssetRecordRequest(
                record_date=datetime(2025, 1, 31),
                asset_class_id=1,
                sub_asset_name="普通預金",
                amount=1000000,
                memo="給与振込",
            )
            response = manager.create_record(request)

            assert response.id is not None
            assert response.record_date == datetime(2025, 1, 31)
            assert response.asset_class_id == 1
            assert response.asset_class_name == "現金"
            assert response.sub_asset_name == "普通預金"
            assert response.amount == 1000000

    def test_get_records(self, temp_db_with_manager):
        """Test retrieving asset records."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)

            # Create test records
            for i in range(3):
                request = AssetRecordRequest(
                    record_date=datetime(2025, 1 + i, 28),
                    asset_class_id=1,
                    sub_asset_name=f"預金 {i+1}",
                    amount=100000 * (i + 1),
                )
                manager.create_record(request)

            records = manager.get_records()
            assert len(records) == 3

    def test_get_records_by_class(self, temp_db_with_manager):
        """Test retrieving records by asset class."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)

            # Create records for different classes
            for class_id in [1, 2, 1]:
                request = AssetRecordRequest(
                    record_date=datetime.now(),
                    asset_class_id=class_id,
                    sub_asset_name="テスト",
                    amount=100000,
                )
                manager.create_record(request)

            # Get records for class 1
            records = manager.get_records(asset_class_id=1)
            assert len(records) == 2
            for record in records:
                assert record.asset_class_id == 1

    def test_get_record(self, temp_db_with_manager):
        """Test retrieving a single record."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)

            request = AssetRecordRequest(
                record_date=datetime(2025, 1, 31),
                asset_class_id=2,
                sub_asset_name="楽天VTI",
                amount=500000,
            )
            created = manager.create_record(request)

            retrieved = manager.get_record(created.id)
            assert retrieved is not None
            assert retrieved.id == created.id
            assert retrieved.sub_asset_name == "楽天VTI"

    def test_get_nonexistent_record(self, temp_db_with_manager):
        """Test retrieving non-existent record."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)
            retrieved = manager.get_record(9999)
            assert retrieved is None

    def test_update_record(self, temp_db_with_manager):
        """Test updating a record."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)

            # Create record
            request = AssetRecordRequest(
                record_date=datetime(2025, 1, 31),
                asset_class_id=1,
                sub_asset_name="普通預金",
                amount=1000000,
            )
            created = manager.create_record(request)

            # Update record
            update_request = AssetRecordRequest(
                record_date=datetime(2025, 2, 28),
                asset_class_id=1,
                sub_asset_name="定期預金",
                amount=1500000,
                memo="更新テスト",
            )
            updated = manager.update_record(created.id, update_request)

            assert updated.id == created.id
            assert updated.record_date == datetime(2025, 2, 28)
            assert updated.sub_asset_name == "定期預金"
            assert updated.amount == 1500000

    def test_delete_record(self, temp_db_with_manager):
        """Test deleting a record (soft delete)."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)

            # Create record
            request = AssetRecordRequest(
                record_date=datetime.now(),
                asset_class_id=1,
                sub_asset_name="削除テスト",
                amount=100000,
            )
            created = manager.create_record(request)

            # Delete record
            success = manager.delete_record(created.id)
            assert success is True

            # Check that record is not retrieved
            retrieved = manager.get_record(created.id)
            assert retrieved is None

    def test_delete_nonexistent_record(self, temp_db_with_manager):
        """Test deleting non-existent record."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)
            success = manager.delete_record(9999)
            assert success is False

    def test_get_asset_classes(self, temp_db_with_manager):
        """Test retrieving asset classes."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)
            classes = manager.get_asset_classes()

            assert len(classes) == 5
            names = [c["name"] for c in classes]
            assert "cash" in names
            assert "stocks" in names
            assert "funds" in names
            assert "realestate" in names
            assert "pension" in names

    def test_get_records_by_date_range(self, temp_db_with_manager):
        """Test retrieving records by date range."""
        with temp_db_with_manager.session_scope() as session:
            manager = AssetManager(session)

            # Create records across different months
            for month in [1, 2, 3]:
                request = AssetRecordRequest(
                    record_date=datetime(2025, month, 28),
                    asset_class_id=1,
                    sub_asset_name=f"月{month}",
                    amount=100000,
                )
                manager.create_record(request)

            # Get records for Feb-Mar
            records = manager.get_records(
                start_date=datetime(2025, 2, 1),
                end_date=datetime(2025, 3, 31),
            )
            assert len(records) == 2
