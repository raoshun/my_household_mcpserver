"""Tests for report generation and export tools."""

import json
from datetime import datetime

import pytest

from household_mcp.database import Budget, Transaction
from household_mcp.database.manager import DatabaseManager
from household_mcp.tools.report_tools import (
    create_summary_report,
    export_transactions,
    generate_report,
)


class TestReportTools:
    """レポート生成ツール テスト."""

    @pytest.fixture
    def db_setup(self):
        """テスト用データベース セットアップ。"""
        manager = DatabaseManager()
        manager.drop_all_tables()
        manager.initialize_database()

        yield manager

    @pytest.fixture
    def sample_transactions(self, db_setup):
        """Create sample transaction data for testing."""
        manager = db_setup
        session = manager.get_session()
        base_date = datetime(2024, 10, 1)

        # Income transactions (positive amounts)
        for i in range(3):
            session.add(
                Transaction(
                    date=base_date.replace(day=min(i + 1, 28)),
                    category_major="給与",
                    category_minor="本給",
                    description="給与（10月）",
                    amount=300000,
                    source_file="test.csv",
                    row_number=1000 + i,
                )
            )

        # Expense transactions (negative amounts) - various categories
        expenses = [
            ("食費", "食事", -5000, 1),
            ("食費", "酒類", -2000, 2),
            ("交通費", "電車", -3000, 3),
            ("交通費", "ガソリン", -4000, 4),
            ("医療", "薬", -1500, 5),
            ("医療", "病院", -8000, 6),
            ("娯楽", "映画", -1500, 7),
            ("生活用品", "日用品", -2500, 8),
        ]

        for i, (major, minor, amount, day) in enumerate(expenses):
            session.add(
                Transaction(
                    date=base_date.replace(day=day),
                    category_major=major,
                    category_minor=minor,
                    description=f"{major}-{minor}",
                    amount=amount,
                    source_file="test.csv",
                    row_number=2000 + i,
                )
            )

        # Add budget entries
        session.add(Budget(year=2024, month=10, category_major="食費", amount=50000))
        session.add(Budget(year=2024, month=10, category_major="交通費", amount=30000))
        session.add(Budget(year=2024, month=10, category_major="医療", amount=20000))

        session.commit()
        session.close()
        return manager

    def test_export_transactions_csv(self, sample_transactions):
        """Test CSV export of transactions."""
        result = export_transactions(2024, 10, format="csv")

        assert isinstance(result, str)
        assert "date" in result
        assert "direction" in result
        assert "category_major" in result
        assert "amount" in result
        # Check for sample data
        assert "給与" in result
        assert "食費" in result
        assert "300000" in result

    def test_export_transactions_json(self, sample_transactions):
        """Test JSON export of transactions."""
        result = export_transactions(2024, 10, format="json")

        data = json.loads(result)
        assert "metadata" in data
        assert "transactions" in data
        assert data["metadata"]["year"] == 2024
        assert data["metadata"]["month"] == 10
        assert data["metadata"]["total_records"] > 0
        assert len(data["transactions"]) == data["metadata"]["total_records"]

    def test_export_transactions_with_category_filter(self, sample_transactions):
        """Test export with category filtering."""
        result = export_transactions(2024, 10, category_major="食費", format="json")

        data = json.loads(result)
        assert data["metadata"]["category_major"] == "食費"
        # Should have 2 food transactions
        assert data["metadata"]["total_records"] == 2
        for tx in data["transactions"]:
            assert tx["category_major"] == "食費"

    def test_export_transactions_invalid_month(self):
        """Test that invalid month raises error."""
        with pytest.raises(ValueError, match="Month must be 1-12"):
            export_transactions(2024, 13)

        with pytest.raises(ValueError, match="Month must be 1-12"):
            export_transactions(2024, 0)

    def test_generate_summary_report(self, sample_transactions):
        """Test summary report generation."""
        result = generate_report(2024, 10, "summary")

        data = json.loads(result)
        assert data["report_type"] == "summary"
        assert data["period"] == "2024-10"
        assert "summary" in data
        assert "income" in data["summary"]
        assert "expense" in data["summary"]
        assert "savings" in data["summary"]
        assert "budget" in data
        assert data["summary"]["income"] == 900000  # 3 x 300000
        assert data["summary"]["expense"] > 0

    def test_generate_detailed_report(self, sample_transactions):
        """Test detailed report with category breakdown."""
        result = generate_report(2024, 10, "detailed")

        data = json.loads(result)
        assert data["report_type"] == "detailed"
        assert "by_category" in data
        assert "totals" in data

        # Check structure
        assert "income" in data["by_category"]
        assert "expense" in data["by_category"]
        assert "給与" in data["by_category"]["income"]
        assert "食費" in data["by_category"]["expense"]

        # Check totals
        assert data["totals"]["income"]["給与"] == 900000
        assert data["totals"]["expense"]["食費"] == 7000  # 5000 + 2000
        assert data["totals"]["expense"]["交通費"] == 7000  # 3000 + 4000

    def test_generate_category_report(self, sample_transactions):
        """Test category analysis report."""
        result = generate_report(2024, 10, "category")

        data = json.loads(result)
        assert data["report_type"] == "category"
        assert "top_expenses" in data
        assert "top_income" in data

        # Check structure of top expenses
        assert len(data["top_expenses"]) > 0
        for item in data["top_expenses"]:
            assert "category" in item
            assert "total" in item
            assert "transaction_count" in item
            assert "average" in item

        # Check structure of top income
        assert len(data["top_income"]) > 0

    def test_create_summary_report(self, sample_transactions):
        """Test comprehensive summary report."""
        result = create_summary_report(2024, 10)

        data = json.loads(result)
        assert "comprehensive_report" in data
        report = data["comprehensive_report"]

        # Check all sections exist
        assert "period" in report
        assert "summary" in report
        assert "budget" in report
        assert "statistics" in report
        assert "category_breakdown" in report
        assert "top_expenses" in report
        assert "top_income" in report

        # Verify data consistency
        assert report["summary"]["income"] == 900000
        assert report["summary"]["expense"] > 0
        assert "savings_rate" in report["summary"]

    def test_generate_report_invalid_type(self, sample_transactions):
        """Test that invalid report type raises error."""
        with pytest.raises(ValueError, match="Unknown report type"):
            generate_report(2024, 10, "invalid_type")

    def test_export_empty_month(self, db_setup):
        """Test export for month with no transactions."""
        result = export_transactions(2024, 11, format="json")

        data = json.loads(result)
        assert data["metadata"]["total_records"] == 0
        assert len(data["transactions"]) == 0

    def test_generate_report_empty_month(self, db_setup):
        """Test report generation for month with no transactions."""
        result = generate_report(2024, 11, "summary")

        data = json.loads(result)
        assert data["summary"]["income"] == 0
        assert data["summary"]["expense"] == 0
        assert data["summary"]["savings"] == 0
