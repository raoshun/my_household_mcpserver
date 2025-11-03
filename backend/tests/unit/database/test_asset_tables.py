"""Test asset tables initialization."""

import pytest
from datetime import datetime
from sqlalchemy import text

from household_mcp.database.manager import DatabaseManager
from household_mcp.database.models import AssetClass, AssetRecord


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_assets.db")
    db = DatabaseManager(db_path=db_path)
    db.initialize_database()
    yield db
    db.close()


class TestAssetClassesTable:
    """Test assets_classes table."""

    def test_create_asset_classes_table(self, temp_db):
        """Test that assets_classes table is created."""
        with temp_db.session_scope() as session:
            # テーブルの存在確認
            result = session.query(AssetClass).all()
            assert len(result) == 5

    def test_asset_classes_initial_data(self, temp_db):
        """Test initial asset class data."""
        with temp_db.session_scope() as session:
            classes = session.query(AssetClass).order_by(AssetClass.id).all()

            expected_classes = [
                ("cash", "現金", "💰"),
                ("stocks", "株", "📈"),
                ("funds", "投資信託", "📊"),
                ("realestate", "不動産", "🏠"),
                ("pension", "年金", "🎯"),
            ]

            for i, (name, display_name, icon) in enumerate(expected_classes):
                assert classes[i].name == name
                assert classes[i].display_name == display_name
                assert classes[i].icon == icon

    def test_asset_classes_have_descriptions(self, temp_db):
        """Test that asset classes have descriptions."""
        with temp_db.session_scope() as session:
            classes = session.query(AssetClass).all()
            for asset_class in classes:
                assert asset_class.description is not None
                assert len(asset_class.description) > 0

    def test_asset_class_creation_timestamp(self, temp_db):
        """Test that asset classes have creation timestamp."""
        with temp_db.session_scope() as session:
            classes = session.query(AssetClass).all()
            for asset_class in classes:
                assert asset_class.created_at is not None
                assert isinstance(asset_class.created_at, datetime)


class TestAssetRecordsTable:
    """Test asset_records table."""

    def test_create_asset_records_table(self, temp_db):
        """Test that asset_records table is created."""
        with temp_db.session_scope() as session:
            asset_class = session.query(AssetClass).first()
            assert asset_class is not None

            # 資産レコードを作成
            record = AssetRecord(
                record_date=datetime.now(),
                asset_class_id=asset_class.id,
                sub_asset_name="普通預金",
                amount=1000000,
                memo="給与振込",
                is_manual=1,
                source_type="manual",
            )
            session.add(record)
            session.flush()

            # 確認
            assert record.id is not None
            assert record.asset_class_id == asset_class.id

    def test_asset_record_with_all_fields(self, temp_db):
        """Test asset record with all fields."""
        with temp_db.session_scope() as session:
            asset_class = (
                session.query(AssetClass).filter_by(name="cash").first()
            )

            record = AssetRecord(
                record_date=datetime(2025, 1, 31),
                asset_class_id=asset_class.id,
                sub_asset_name="普通預金",
                amount=1000000,
                memo="給与振込",
                is_deleted=0,
                is_manual=1,
                source_type="manual",
                linked_transaction_id=None,
                created_by="user",
            )
            session.add(record)
            session.flush()

            retrieved = session.query(AssetRecord).first()
            assert retrieved.record_date == datetime(2025, 1, 31)
            assert retrieved.sub_asset_name == "普通預金"
            assert retrieved.amount == 1000000
            assert retrieved.memo == "給与振込"
            assert retrieved.is_manual == 1

    def test_asset_record_with_relationship(self, temp_db):
        """Test asset record relationship to asset class."""
        with temp_db.session_scope() as session:
            asset_class = (
                session.query(AssetClass).filter_by(name="stocks").first()
            )

            record = AssetRecord(
                record_date=datetime(2025, 2, 28),
                asset_class_id=asset_class.id,
                sub_asset_name="楽天VTI",
                amount=500000,
            )
            session.add(record)
            session.flush()

            retrieved = (
                session.query(AssetRecord)
                .filter_by(sub_asset_name="楽天VTI")
                .first()
            )
            assert retrieved.asset_class.name == "stocks"
            assert retrieved.asset_class.display_name == "株"

    def test_asset_record_default_values(self, temp_db):
        """Test asset record default values."""
        with temp_db.session_scope() as session:
            asset_class = session.query(AssetClass).first()

            record = AssetRecord(
                record_date=datetime.now(),
                asset_class_id=asset_class.id,
                sub_asset_name="テスト資産",
                amount=100000,
            )
            session.add(record)
            session.flush()

            retrieved = session.query(AssetRecord).first()
            assert retrieved.is_deleted == 0
            assert retrieved.is_manual == 1
            assert retrieved.source_type == "manual"
            assert retrieved.linked_transaction_id is None
            assert retrieved.created_by == "user"

    def test_asset_record_timestamps(self, temp_db):
        """Test asset record timestamps."""
        with temp_db.session_scope() as session:
            asset_class = session.query(AssetClass).first()
            now = datetime.now()

            record = AssetRecord(
                record_date=now,
                asset_class_id=asset_class.id,
                sub_asset_name="タイムスタンプテスト",
                amount=100000,
            )
            session.add(record)
            session.flush()

            retrieved = session.query(AssetRecord).first()
            assert retrieved.created_at is not None
            assert retrieved.updated_at is not None
            assert isinstance(retrieved.created_at, datetime)
            assert isinstance(retrieved.updated_at, datetime)


class TestAssetTablesSchema:
    """Test table schema and indexes."""

    def test_asset_classes_unique_name(self, temp_db):
        """Test that asset class names are unique."""
        with temp_db.session_scope() as session:
            # 同じ名前で別の資産クラスを作成しようとする
            duplicate = AssetClass(
                name="cash",
                display_name="現金2",
                description="テスト",
                icon="💵",
            )
            session.add(duplicate)
            # flush時に例外が発生するはず
            try:
                session.flush()
                # フラッシュが成功した場合はロールバック
                session.rollback()
                pytest.fail("Expected IntegrityError but nothing was raised")
            except Exception as e:
                # IntegrityErrorが発生することを確認
                assert "UNIQUE" in str(e) or "unique" in str(e).lower()
                session.rollback()

    def test_asset_record_indexes_exist(self, temp_db):
        """Test that indexes are created."""
        # SQLiteのインデックス情報を取得
        with temp_db.engine.connect() as conn:
            query = text(
                "SELECT name FROM sqlite_master "
                "WHERE type='index' AND tbl_name='asset_records'"
            )
            result = conn.execute(query)
            indexes = [row[0] for row in result]
            # 複数のインデックスが存在することを確認
            assert len(indexes) > 0

    def test_asset_record_foreign_key_constraint(self, temp_db):
        """Test foreign key constraint."""
        # 存在しないasset_class_idで作成しようとする
        record = AssetRecord(
            record_date=datetime.now(),
            asset_class_id=9999,  # 存在しないID
            sub_asset_name="テスト",
            amount=100000,
        )

        with temp_db.session_scope() as session:
            session.add(record)
            # flush時に例外が発生するはず
            try:
                session.flush()
                # フラッシュが成功した場合はロールバック
                session.rollback()
                pytest.fail("Expected ForeignKeyError but nothing was raised")
            except Exception as e:
                # ForeignKeyErrorが発生することを確認
                assert "FOREIGN" in str(e) or "foreign" in str(e).lower()
                session.rollback()
