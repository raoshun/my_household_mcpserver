"""Tests for DB-based trend tools (TASK-1401)."""

from datetime import datetime

import pytest

from household_mcp.database import Transaction
from household_mcp.database.manager import DatabaseManager
from household_mcp.tools.trend_tool_db import get_category_trend, get_monthly_summary


class TestDBTrendTools:
    """DB-based trend tools テスト."""

    @pytest.fixture
    def db_setup(self):
        """テスト用データベース セットアップ。"""
        manager = DatabaseManager()
        manager.drop_all_tables()
        manager.initialize_database()

        session = manager.get_session()
        try:
            # 2024年11月のテスト取引データを追加
            base_date = datetime(2024, 11, 1)

            # 食費（支出）
            for i in range(10):
                tx = Transaction(
                    source_file="test.csv",
                    row_number=1000 + i,
                    date=base_date.replace(day=i + 1),
                    amount=-1500 - i * 100,
                    category_major="食費",
                    category_minor="外食",
                    description=f"食事 {i}",
                )
                session.add(tx)

            # 交通費（支出）
            for i in range(5):
                tx = Transaction(
                    source_file="test.csv",
                    row_number=2000 + i,
                    date=base_date.replace(day=i + 1),
                    amount=-500 - i * 50,
                    category_major="交通費",
                    category_minor="電車",
                    description=f"移動 {i}",
                )
                session.add(tx)

            # 給料（収入）
            tx = Transaction(
                source_file="test.csv",
                row_number=3000,
                date=base_date.replace(day=1),
                amount=300000,
                category_major="収入",
                category_minor="給料",
                description="11月給料",
            )
            session.add(tx)

            session.commit()
            yield session
        finally:
            session.close()
            manager.drop_all_tables()

    def test_get_category_trend_with_specific_category(self, db_setup):
        """特定カテゴリのトレンド取得。"""
        result = get_category_trend(category="食費", top_n=3)

        assert result["category"] == "食費"
        assert result["total_amount"] < 0  # 支出
        assert result["transaction_count"] == 10
        assert "start_month" in result
        assert "end_month" in result

    def test_get_category_trend_top_categories(self, db_setup):
        """トップカテゴリの取得。"""
        result = get_category_trend(top_n=3)

        assert result["category"] is None
        assert "top_categories" in result
        assert "details" in result
        assert len(result["details"]) > 0

    def test_get_monthly_summary(self, db_setup):
        """月次サマリーの取得。"""
        result = get_monthly_summary(year=2024, month=11)

        assert result["year"] == 2024
        assert result["month"] == 11
        assert result["income"] > 0  # 給料あり
        assert result["expense"] > 0  # 支出あり
        assert "savings_rate" in result
        assert isinstance(result["categories"], list)

    def test_get_category_trend_with_date_range(self, db_setup):
        """日付範囲指定のトレンド取得。"""
        result = get_category_trend(
            start_year=2024,
            start_month=11,
            end_year=2024,
            end_month=11,
        )

        assert result["start_month"] == "2024-11"
        assert result["end_month"] == "2024-11"

    def test_get_category_trend_nonexistent_category(self, db_setup):
        """存在しないカテゴリの処理。"""
        from household_mcp.exceptions import DataSourceError

        with pytest.raises(DataSourceError):
            get_category_trend(category="存在しないカテゴリ")
