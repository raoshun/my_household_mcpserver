"""Tests for advanced analytics tools (TASK-1402)."""

from datetime import datetime

import pytest

from household_mcp.database import Transaction
from household_mcp.database.manager import DatabaseManager
from household_mcp.tools.analytics_tools import (
    get_monthly_comparison,
    get_moving_average,
    get_yoy_comparison,
    predict_expense,
)


class TestAnalyticsTools:
    """Advanced analytics tools テスト."""

    @pytest.fixture
    def db_setup(self):
        """テスト用データベース セットアップ。"""
        manager = DatabaseManager()
        manager.drop_all_tables()
        manager.initialize_database()

        session = manager.get_session()
        try:
            # 2024年10月、11月、12月、2025年1月のテスト取引データを追加
            months_data = [
                (2024, 10),
                (2024, 11),
                (2024, 12),
                (2025, 1),
            ]

            for year, month in months_data:
                base_date = datetime(year, month, 1)
                # Unique offset per month
                month_offset = sum(1 for y, m in months_data if (y, m) < (year, month))

                # 食費（支出）- 月ごとに変動
                if month == 10:
                    expense_amount = -1500
                elif month == 11:
                    expense_amount = -1800
                elif month == 12:
                    expense_amount = -1600
                else:
                    expense_amount = -2000

                for i in range(10):
                    tx = Transaction(
                        source_file="test.csv",
                        row_number=1000 + month_offset * 100 + i,
                        date=base_date.replace(day=min(i + 1, 28)),
                        amount=expense_amount - i * 100,
                        category_major="食費",
                        category_minor="外食",
                        description=f"食事 {i}",
                    )
                    session.add(tx)

                # 交通費（支出）
                if month == 10:
                    transport_amount = -500
                elif month == 11:
                    transport_amount = -600
                elif month == 12:
                    transport_amount = -550
                else:
                    transport_amount = -700

                for i in range(5):
                    tx = Transaction(
                        source_file="test.csv",
                        row_number=2000 + month_offset * 100 + i,
                        date=base_date.replace(day=min(i + 1, 28)),
                        amount=transport_amount - i * 50,
                        category_major="交通費",
                        category_minor="電車",
                        description=f"移動 {i}",
                    )
                    session.add(tx)

                # 給料（収入）
                salary = 300000 if month in [10, 11, 12] else 320000
                tx = Transaction(
                    source_file="test.csv",
                    row_number=3000 + month_offset * 100,
                    date=base_date.replace(day=1),
                    amount=salary,
                    category_major="収入",
                    category_minor="給料",
                    description=f"{year}年{month}月給料",
                )
                session.add(tx)

            session.commit()
            yield session
        finally:
            session.close()
            manager.drop_all_tables()

    def test_get_monthly_comparison(self, db_setup):
        """前月比較の取得。"""
        # 2025年1月と前月（2024年12月）の比較
        result = get_monthly_comparison(year=2025, month=1)

        assert result["current_month"] == "2025-01"
        assert result["previous_month"] == "2024-12"
        assert "expense_difference" in result
        assert "expense_difference_pct" in result
        assert "income_difference" in result
        assert result["current_expense"] > 0
        assert result["previous_expense"] > 0

    def test_get_yoy_comparison(self, db_setup):
        """前年同月比較の取得。"""
        result = get_yoy_comparison(year=2025, month=1)

        # 2025年1月と2024年1月の比較（2024年1月はテストデータにないので値は0）
        assert result["current_year"] == 2025
        assert result["previous_year"] == 2024
        assert result["month"] == 1
        assert "expense_difference_pct" in result

    def test_get_moving_average(self, db_setup):
        """12ヶ月移動平均の計算。"""
        result = get_moving_average(months=3, year=2025, month=1)

        assert result["period_months"] == 3
        assert result["end_month"] == "2025-01"
        assert "moving_average" in result
        assert len(result["monthly_breakdown"]) == 3
        assert result["moving_average"] > 0
        assert result["min_expense"] >= 0
        assert result["max_expense"] >= result["min_expense"]

    def test_predict_expense(self, db_setup):
        """支出予測の取得。"""
        result = predict_expense(year=2025, month=1)

        assert "prediction_month" in result
        assert "predicted_expense" in result
        assert result["predicted_expense"] > 0
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert "confidence_reason" in result
        assert len(result["last_3_months"]) == 3
