"""クエリ最適化モジュールのテスト。

QueryOptimizer、AggregationOptimizer、IndexManager の機能を検証します。
"""

from datetime import datetime, timedelta

import pytest

from household_mcp.database import Transaction
from household_mcp.database.manager import DatabaseManager
from household_mcp.database.query_optimization import (
    AggregationOptimizer,
    IndexManager,
    QueryOptimizer,
)


class TestQueryOptimizer:
    """QueryOptimizer 機能テスト。"""

    @pytest.fixture
    def db_setup(self):
        """テスト用のデータベース セットアップ。"""
        manager = DatabaseManager()
        manager.drop_all_tables()
        manager.initialize_database()

        session = manager.get_session()
        try:
            # テスト用取引データを追加
            base_date = datetime(2024, 1, 1)
            for i in range(100):
                tx = Transaction(
                    source_file="test.csv",
                    row_number=i + 1000,
                    date=base_date + timedelta(days=i % 30),
                    amount=-1000 - i * 10,
                    category_major="食費" if i % 2 == 0 else "交通費",
                    category_minor="外食" if i % 2 == 0 else "電車",
                    description=f"テスト取引 {i}",
                )
                session.add(tx)
            session.commit()
            yield session
        finally:
            session.close()
            manager.drop_all_tables()

    def test_get_index_strategies(self, db_setup):
        """インデックス戦略を取得できる。"""
        optimizer = QueryOptimizer(db_setup)
        strategies = optimizer.get_index_strategies()

        assert len(strategies) > 0
        assert all(s.index_name for s in strategies)
        assert all(s.table_name for s in strategies)
        assert all(s.columns for s in strategies)

    def test_get_table_stats(self, db_setup):
        """テーブル統計情報を取得できる。"""
        optimizer = QueryOptimizer(db_setup)
        stats = optimizer.get_table_stats()

        assert "transactions" in stats
        assert stats["transactions"]["record_count"] == 100
        assert stats["transactions"]["table_size_bytes"] >= 0


class TestAggregationOptimizer:
    """AggregationOptimizer 機能テスト。"""

    @pytest.fixture
    def db_setup(self):
        """テスト用のデータベース セットアップ。"""
        manager = DatabaseManager()
        manager.drop_all_tables()
        manager.initialize_database()

        session = manager.get_session()
        try:
            # テスト用取引データを追加
            base_date = datetime(2024, 1, 1)
            for i in range(50):
                tx = Transaction(
                    source_file="test.csv",
                    row_number=i + 2000,
                    date=base_date + timedelta(days=i % 10),
                    amount=-1000 - i * 10,
                    category_major="食費",
                    category_minor="外食",
                    description=f"テスト取引 {i}",
                )
                session.add(tx)
            session.commit()
            yield session
        finally:
            session.close()
            manager.drop_all_tables()

    def test_get_monthly_category_summary(self, db_setup):
        """月次カテゴリ別サマリを取得できる。"""
        agg_optimizer = AggregationOptimizer(db_setup)
        df = agg_optimizer.get_monthly_category_summary(2024, 1)

        assert not df.empty
        assert "category_major" in df.columns or "category_minor" in df.columns

    def test_get_top_categories(self, db_setup):
        """トップカテゴリを取得できる。"""
        agg_optimizer = AggregationOptimizer(db_setup)
        df = agg_optimizer.get_top_categories(limit=5)

        assert not df.empty
        assert len(df) <= 5


class TestIndexManager:
    """IndexManager 機能テスト。"""

    @pytest.fixture
    def db_setup(self):
        """テスト用のデータベース セットアップ。"""
        manager = DatabaseManager()
        manager.drop_all_tables()
        manager.initialize_database()

        session = manager.get_session()
        try:
            yield session
        finally:
            session.close()
            manager.drop_all_tables()

    def test_get_existing_indexes(self, db_setup):
        """既存のインデックス情報を取得できる。"""
        index_manager = IndexManager(db_setup)
        indexes = index_manager.get_existing_indexes()

        assert isinstance(indexes, dict)
        assert "transactions" in indexes

    def test_analyze_statistics(self, db_setup):
        """統計情報を分析できる。"""
        index_manager = IndexManager(db_setup)
        result = index_manager.analyze_statistics()

        assert result is True

    def test_vacuum(self, db_setup):
        """データベースの最適化を実行できる。"""
        index_manager = IndexManager(db_setup)
        result = index_manager.vacuum()

        assert result is True
