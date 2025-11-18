"""Tests for budget_analyzer module."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pandas as pd
import pytest

from household_mcp.budget_analyzer import COLUMNS_MAP, BudgetAnalyzer


class TestBudgetAnalyzer:
    """Test suite for BudgetAnalyzer class."""

    @pytest.fixture
    def sample_csv_data(self):
        """Create sample CSV data for testing."""
        data = {
            "calc_target": [1, 1, 1, 0],
            "date": ["2024-01-05", "2024-01-10", "2024-01-15", "2024-02-01"],
            "description": ["給料", "食費", "交通費", "振替"],
            "amount": [300000, -5000, -2000, 10000],
            "institution": ["銀行A", "現金", "カード", "銀行B"],
            "major_category": ["収入", "食費", "交通", "振替"],
            "minor_category": ["給与所得", "外食", "電車", "内部"],
            "memo": ["", "", "", ""],
            "transfer": [0, 0, 0, 1],
            "id": ["001", "002", "003", "004"],
        }
        return pd.DataFrame(data)

    @pytest.fixture
    def temp_csv_file(self, sample_csv_data):
        """Create temporary CSV file with sample data."""
        with NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as f:
            sample_csv_data.to_csv(f, index=False)
            temp_path = Path(f.name)
        yield temp_path
        temp_path.unlink()

    def test_init(self):
        """Test BudgetAnalyzer initialization."""
        analyzer = BudgetAnalyzer(Path("test.csv"))
        assert analyzer.csv_path == Path("test.csv")
        assert analyzer.encoding == "shift_jis"
        assert analyzer.df.empty
        assert list(analyzer.df.columns) == list(COLUMNS_MAP.values())

    def test_init_custom_encoding(self):
        """Test initialization with custom encoding."""
        analyzer = BudgetAnalyzer(Path("test.csv"), encoding="utf-8")
        assert analyzer.encoding == "utf-8"

    def test_load_data_success(self, temp_csv_file):
        """Test successful data loading."""
        analyzer = BudgetAnalyzer(temp_csv_file, encoding="utf-8")
        analyzer.load_data()

        assert not analyzer.df.empty
        assert len(analyzer.df) == 4
        assert "date" in analyzer.df.columns
        assert pd.api.types.is_datetime64_any_dtype(analyzer.df["date"])
        assert pd.api.types.is_numeric_dtype(analyzer.df["amount"])

    def test_load_data_file_not_found(self):
        """Test loading with non-existent file."""
        analyzer = BudgetAnalyzer(Path("nonexistent.csv"))
        analyzer.load_data()

        assert analyzer.df.empty
        assert list(analyzer.df.columns) == list(COLUMNS_MAP.values())

    def test_get_monthly_summary_no_data(self):
        """Test monthly summary with no data loaded."""
        analyzer = BudgetAnalyzer(Path("test.csv"))
        result = analyzer.get_monthly_summary(2024, 1)

        assert result == {"message": "No data available."}

    def test_get_monthly_summary_with_data(self, temp_csv_file):
        """Test monthly summary with loaded data."""
        analyzer = BudgetAnalyzer(temp_csv_file, encoding="utf-8")
        analyzer.load_data()

        result = analyzer.get_monthly_summary(2024, 1)

        assert "period" in result
        assert result["period"] == "2024-01"
        assert result["total_income"] == 300000
        assert result["total_expense"] == 7000
        assert result["balance"] == 293000
        assert "expense_by_category" in result
        assert result["transaction_count"] == 3  # Excludes transfer

    def test_get_monthly_summary_no_data_for_period(self, temp_csv_file):
        """Test monthly summary for period with no data."""
        analyzer = BudgetAnalyzer(temp_csv_file, encoding="utf-8")
        analyzer.load_data()

        result = analyzer.get_monthly_summary(2023, 12)

        assert "message" in result
        assert result["message"] == "No data for 2023-12."

    def test_get_monthly_summary_february(self, temp_csv_file):
        """Test monthly summary for February data."""
        analyzer = BudgetAnalyzer(temp_csv_file, encoding="utf-8")
        analyzer.load_data()

        result = analyzer.get_monthly_summary(2024, 2)

        assert result["period"] == "2024-02"
        assert result["transaction_count"] == 1
