"""Test DatabaseManager initialization."""

import os
import tempfile
from datetime import datetime

from household_mcp.database import DatabaseManager, DuplicateCheck, Transaction


def test_database_manager_initialization():
    """データベース初期化のテスト."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_manager = DatabaseManager(db_path)

        # データベースファイルがまだ存在しないことを確認
        assert not db_manager.database_exists()

        # データベースを初期化
        db_manager.initialize_database()

        # データベースファイルが作成されたことを確認
        assert db_manager.database_exists()
        assert os.path.exists(db_path)

        # クローズ
        db_manager.close()


def test_session_scope():
    """セッションスコープのテスト."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_manager = DatabaseManager(db_path)
        db_manager.initialize_database()

        # トランザクションを追加
        with db_manager.session_scope() as session:
            transaction = Transaction(
                source_file="test.csv",
                row_number=1,
                date=datetime(2025, 1, 1),
                amount=1000.00,
                description="テスト取引",
                category_major="食費",
                category_minor="外食",
            )
            session.add(transaction)

        # データが保存されたことを確認
        with db_manager.session_scope() as session:
            result = session.query(Transaction).filter_by(row_number=1).first()
            assert result is not None
            assert result.source_file == "test.csv"
            assert result.description == "テスト取引"
            assert float(result.amount) == 1000.00

        db_manager.close()


def test_duplicate_check_creation():
    """重複チェックレコードの作成テスト."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db_manager = DatabaseManager(db_path)
        db_manager.initialize_database()

        # 2つのトランザクションを作成
        with db_manager.session_scope() as session:
            t1 = Transaction(
                source_file="test.csv",
                row_number=1,
                date=datetime(2025, 1, 1),
                amount=1000.00,
                description="取引1",
            )
            t2 = Transaction(
                source_file="test.csv",
                row_number=2,
                date=datetime(2025, 1, 1),
                amount=1000.00,
                description="取引2",
            )
            session.add_all([t1, t2])

        # 重複チェックレコードを作成
        with db_manager.session_scope() as session:
            transactions = session.query(Transaction).all()
            assert len(transactions) == 2

            check = DuplicateCheck(
                transaction_id_1=transactions[0].id,
                transaction_id_2=transactions[1].id,
                detection_date_tolerance=0,
                detection_amount_tolerance_abs=0,
                similarity_score=0.95,
                user_decision="duplicate",
            )
            session.add(check)

        # 重複チェックが保存されたことを確認
        with db_manager.session_scope() as session:
            result = session.query(DuplicateCheck).first()
            assert result is not None
            assert result.user_decision == "duplicate"
            assert result.similarity_score is not None
            assert float(result.similarity_score) == 0.95

        db_manager.close()


if __name__ == "__main__":
    # 簡易テスト実行
    test_database_manager_initialization()
    print("✓ Database initialization test passed")

    test_session_scope()
    print("✓ Session scope test passed")

    test_duplicate_check_creation()
    print("✓ Duplicate check creation test passed")

    print("\nAll tests passed!")
