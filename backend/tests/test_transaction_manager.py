"""トランザクション管理モジュールのテスト。

TransactionManager とリトライ機構を検証します。
"""

from datetime import datetime

import pytest

from household_mcp.database import Transaction
from household_mcp.database.manager import DatabaseManager
from household_mcp.database.transaction_manager import (
    RetryConfig,
    TransactionError,
    TransactionManager,
    get_transaction_manager,
)


class TestRetryConfig:
    """RetryConfig テスト。"""

    def test_default_retry_config(self):
        """デフォルト設定を確認。"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.backoff_ms == 100
        assert config.backoff_multiplier == 1.0

    def test_get_wait_ms(self):
        """待機時間計算を検証。"""
        config = RetryConfig(backoff_ms=100, backoff_multiplier=1.0)
        assert config.get_wait_ms(0) == 100
        assert config.get_wait_ms(1) == 100
        assert config.get_wait_ms(2) == 100

    def test_get_wait_ms_with_multiplier(self):
        """乗数付き待機時間計算を検証。"""
        config = RetryConfig(backoff_ms=100, backoff_multiplier=2.0)
        assert config.get_wait_ms(0) == 100
        assert config.get_wait_ms(1) == 200
        assert config.get_wait_ms(2) == 400


class TestTransactionManager:
    """TransactionManager テスト。"""

    @pytest.fixture
    def db_setup(self):
        """テスト用データベース セットアップ。"""
        manager = DatabaseManager()
        manager.drop_all_tables()
        manager.initialize_database()
        yield manager
        manager.drop_all_tables()

    @pytest.fixture
    def tm(self, db_setup):
        """TransactionManager インスタンス。"""
        return TransactionManager(db_setup)

    def test_session_scope_commit(self, tm):
        """session_scope でコミット成功を検証。"""
        with tm.session_scope() as session:
            tx = Transaction(
                source_file="test.csv",
                row_number=1001,
                date=datetime(2024, 1, 1),
                amount=-1000,
                category_major="食費",
                category_minor="外食",
                description="テスト",
            )
            session.add(tx)

        # コミット確認
        with tm.session_scope() as session:
            result = session.query(Transaction).filter_by(row_number=1001).first()
            assert result is not None
            assert result.amount == -1000

    def test_session_scope_rollback_on_error(self, tm):
        """session_scope でエラー時ロールバックを検証。"""
        with pytest.raises(TransactionError):
            with tm.session_scope() as session:
                tx = Transaction(
                    source_file="test.csv",
                    row_number=1002,
                    date=datetime(2024, 1, 1),
                    amount=-1000,
                    category_major="食費",
                    category_minor="外食",
                    description="テスト",
                )
                session.add(tx)
                raise ValueError("意図的なエラー")

        # ロールバック確認（レコードが存在しない）
        with tm.session_scope() as session:
            result = session.query(Transaction).filter_by(row_number=1002).first()
            assert result is None

    def test_execute_in_transaction_success(self, tm):
        """execute_in_transaction で成功を検証。"""

        def add_transaction(session):
            tx = Transaction(
                source_file="test.csv",
                row_number=1003,
                date=datetime(2024, 1, 1),
                amount=-1000,
                category_major="食費",
                category_minor="外食",
                description="テスト",
            )
            session.add(tx)
            return tx

        result = tm.execute_in_transaction(add_transaction)
        assert result.row_number == 1003

    def test_execute_in_transaction_failure(self, tm):
        """execute_in_transaction で失敗を検証。"""

        def failing_transaction(session):
            raise ValueError("意図的なエラー")

        with pytest.raises(TransactionError):
            tm.execute_in_transaction(failing_transaction)

    def test_execute_with_retry_success_first_try(self, tm):
        """execute_with_retry で初回成功を検証。"""
        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = tm.execute_with_retry(func)
        assert result == "success"
        assert call_count == 1

    def test_execute_with_retry_after_retries(self, tm):
        """execute_with_retry でリトライ後成功を検証。"""
        from sqlalchemy.exc import OperationalError

        call_count = 0

        def func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                # OperationalError をシミュレート（リトライ対象）
                raise OperationalError("一時的なエラー", None, None)
            return "success"

        # IntegrityError か OperationalError のみリトライ対象
        result = tm.execute_with_retry(
            func,
            retry_config=RetryConfig(max_retries=2, backoff_ms=10),
        )
        assert result == "success"
        assert call_count == 2

    def test_execute_with_retry_config(self, tm):
        """execute_with_retry でカスタム設定を使用。"""
        config = RetryConfig(max_retries=2, backoff_ms=10)

        def func():
            return "success"

        result = tm.execute_with_retry(func, retry_config=config)
        assert result == "success"

    def test_rollback_and_close(self, tm):
        """rollback_and_close を検証。"""
        session = tm._db_manager.get_session()
        tx = Transaction(
            source_file="test.csv",
            row_number=1004,
            date=datetime(2024, 1, 1),
            amount=-1000,
            category_major="食費",
            category_minor="外食",
            description="テスト",
        )
        session.add(tx)

        tm.rollback_and_close(session)

        # ロールバック確認
        with tm.session_scope() as session:
            result = session.query(Transaction).filter_by(row_number=1004).first()
            assert result is None

    def test_session_scope_nested(self, tm):
        """session_scope_nested を検証。"""
        with tm.session_scope() as outer_session:
            tx1 = Transaction(
                source_file="test.csv",
                row_number=1005,
                date=datetime(2024, 1, 1),
                amount=-1000,
                category_major="食費",
                category_minor="外食",
                description="外側",
            )
            outer_session.add(tx1)

            with tm.session_scope_nested(outer_session) as inner_session:
                tx2 = Transaction(
                    source_file="test.csv",
                    row_number=1006,
                    date=datetime(2024, 1, 1),
                    amount=-500,
                    category_major="食費",
                    category_minor="弁当",
                    description="内側",
                )
                inner_session.add(tx2)

        # 両方がコミットされたか確認
        with tm.session_scope() as session:
            result1 = session.query(Transaction).filter_by(row_number=1005).first()
            result2 = session.query(Transaction).filter_by(row_number=1006).first()
            assert result1 is not None
            assert result2 is not None


class TestGlobalTransactionManager:
    """グローバル TransactionManager テスト。"""

    def test_get_transaction_manager_singleton(self):
        """get_transaction_manager が同じインスタンスを返すか検証。"""
        tm1 = get_transaction_manager()
        tm2 = get_transaction_manager()
        assert tm1 is tm2
