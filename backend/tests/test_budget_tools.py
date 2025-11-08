"""Tests for budget management tools (TASK-1403)."""

from datetime import datetime

import pytest

from household_mcp.database import Transaction
from household_mcp.database.manager import DatabaseManager
from household_mcp.tools.budget_tools import (
    compare_budget_actual,
    get_budget_status,
    get_budget_summary,
    set_budget,
)


class TestBudgetTools:
    """Budget management tools テスト."""

    @pytest.fixture
    def db_setup(self):
        """テスト用データベース セットアップ。"""
        manager = DatabaseManager()
        manager.drop_all_tables()
        manager.initialize_database()

        session = manager.get_session()
        try:
            base_date = datetime(2025, 1, 1)

            # 食費の取引データ（予算：3000円）
            for i in range(10):
                tx = Transaction(
                    source_file="test.csv",
                    row_number=1000 + i,
                    date=base_date.replace(day=min(i + 1, 28)),
                    amount=-300 - i * 10,  # Total: ~3450 (over budget)
                    category_major="食費",
                    category_minor="外食",
                    description=f"食事 {i}",
                )
                session.add(tx)

            # 交通費の取引データ（予算：1000円）
            for i in range(5):
                tx = Transaction(
                    source_file="test.csv",
                    row_number=2000 + i,
                    date=base_date.replace(day=min(i + 1, 28)),
                    amount=-100 - i * 10,  # Total: ~550 (under budget)
                    category_major="交通費",
                    category_minor="電車",
                    description=f"移動 {i}",
                )
                session.add(tx)

            session.commit()
            yield session
        finally:
            session.close()
            manager.drop_all_tables()

    def test_set_budget_create(self, db_setup):
        """予算の新規作成。"""
        result = set_budget(
            year=2025,
            month=1,
            category_major="食費",
            amount=3000.0,
        )

        assert result["status"] == "created"
        assert result["year"] == 2025
        assert result["month"] == 1
        assert result["category"] == "食費"
        assert result["amount"] == 3000.0

    def test_set_budget_update(self, db_setup):
        """予算の更新。"""
        # Create first
        set_budget(
            year=2025,
            month=1,
            category_major="食費",
            amount=3000.0,
        )

        # Update
        result = set_budget(
            year=2025,
            month=1,
            category_major="食費",
            amount=3500.0,
        )

        assert result["status"] == "updated"
        assert result["amount"] == 3500.0

    def test_get_budget_status(self, db_setup):
        """予算ステータスの取得（over budget）。"""
        # Set budget
        set_budget(
            year=2025,
            month=1,
            category_major="食費",
            amount=3000.0,
        )

        # Get status
        result = get_budget_status(
            year=2025,
            month=1,
            category_major="食費",
        )

        assert result["year"] == 2025
        assert result["month"] == 1
        assert result["budget_amount"] == 3000.0
        assert result["actual_amount"] > 3000.0  # Over budget
        assert result["is_over_budget"] is True
        assert result["achievement_rate_pct"] > 100

    def test_get_budget_summary(self, db_setup):
        """予算サマリーの取得。"""
        # Set budgets
        set_budget(
            year=2025,
            month=1,
            category_major="食費",
            amount=3000.0,
        )
        set_budget(
            year=2025,
            month=1,
            category_major="交通費",
            amount=1000.0,
        )

        # Get summary
        result = get_budget_summary(year=2025, month=1)

        assert result["year"] == 2025
        assert result["month"] == 1
        assert result["total_budget"] == 4000.0
        assert len(result["categories"]) == 2
        assert result["total_actual"] > 0

    def test_compare_budget_actual(self, db_setup):
        """予算実績比較テーブルの取得。"""
        # Set budgets
        set_budget(
            year=2025,
            month=1,
            category_major="食費",
            amount=3000.0,
        )
        set_budget(
            year=2025,
            month=1,
            category_major="交通費",
            amount=1000.0,
        )

        # Compare
        result = compare_budget_actual(year=2025, month=1)

        assert result["period"] == "2025-01"
        assert "comparison_table" in result
        assert "summary" in result
        assert len(result["comparison_table"]) == 2
        assert result["summary"]["total_budget"] == 4000.0
