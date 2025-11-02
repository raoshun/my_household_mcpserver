"""Tests for category_analysis tool."""

import os
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from household_mcp.analysis.trends import TrendMetrics


class TestCategoryAnalysisTool:
    """Tests for category_analysis tool functionality."""

    @pytest.fixture
    def mock_data_loader(self):
        """Mock HouseholdDataLoader."""
        loader = MagicMock()
        loader.iter_available_months.return_value = iter(
            [
                date(2025, 1, 1),
                date(2025, 2, 1),
                date(2025, 3, 1),
            ]
        )
        return loader

    @pytest.fixture
    def mock_analyzer(self):
        """Mock CategoryTrendAnalyzer."""
        analyzer = MagicMock()
        # Return sample metrics for 3 months
        analyzer.metrics_for_category.return_value = [
            TrendMetrics(
                category="食費",
                month=date(2025, 3, 1),
                amount=-50000,
                month_over_month=10.0,
                year_over_year=5.0,
                moving_average=-48000.0,
            ),
            TrendMetrics(
                category="食費",
                month=date(2025, 2, 1),
                amount=-45000,
                month_over_month=-5.0,
                year_over_year=2.0,
                moving_average=-47000.0,
            ),
            TrendMetrics(
                category="食費",
                month=date(2025, 1, 1),
                amount=-47000,
                month_over_month=8.0,
                year_over_year=3.0,
                moving_average=-46000.0,
            ),
        ]
        return analyzer

    @pytest.mark.skip(
        reason="Mocking internal _server module functions requires refactoring"
    )
    def test_category_analysis_success(self, mock_data_loader, mock_analyzer):
        """Test category_analysis with valid data."""
        from household_mcp.server import category_analysis

        # Execute
        result = category_analysis(category="食費", months=3)

        # Verify
        assert "error" not in result
        assert result["category"] == "食費"
        assert result["months"] == 3
        assert result["total_expense"] == 142000  # 50000 + 45000 + 47000
        assert result["average_expense"] == 47333  # 142000 / 3
        assert "summary" in result
        assert "食費" in result["summary"]
        assert "monthly_breakdown" in result
        assert len(result["monthly_breakdown"]) == 3

        # Verify monthly breakdown structure
        for month_data in result["monthly_breakdown"]:
            assert "year" in month_data
            assert "month" in month_data
            assert "amount" in month_data
            assert "mom_change" in month_data

    @pytest.mark.skip(
        reason="Mocking internal _server module functions requires refactoring"
    )
    def test_category_analysis_no_data(self, mock_data_loader):
        """Test category_analysis when no CSV files are available."""
        pass  # noqa: F401

    @patch("household_mcp.server._get_data_loader")
    @patch("household_mcp.server._data_dir")
    @patch("household_mcp.analysis.trends.CategoryTrendAnalyzer")
    def test_category_analysis_category_not_found(
        self, mock_analyzer_class, mock_data_dir, mock_get_loader, mock_data_loader
    ):
        """Test category_analysis when specified category doesn't exist."""
        from household_mcp.server import category_analysis

        # Setup mocks
        mock_get_loader.return_value = mock_data_loader
        mock_data_dir.return_value = "data"

        analyzer = MagicMock()
        analyzer.metrics_for_category.return_value = []  # No data for this category
        mock_analyzer_class.return_value = analyzer

        # Execute
        result = category_analysis(category="存在しないカテゴリ", months=3)

        # Verify Japanese error message
        assert "error" in result
        assert "存在しないカテゴリ" in result["error"]
        assert "データが見つかりませんでした" in result["error"]

    @patch("household_mcp.server._get_data_loader")
    @patch("household_mcp.server._data_dir")
    @patch("household_mcp.analysis.trends.CategoryTrendAnalyzer")
    def test_category_analysis_analyzer_exception(
        self, mock_analyzer_class, mock_data_dir, mock_get_loader, mock_data_loader
    ):
        """Test category_analysis when CategoryTrendAnalyzer raises generic exception."""
        from household_mcp.server import category_analysis

        # Setup mocks
        mock_get_loader.return_value = mock_data_loader
        mock_data_dir.return_value = "data"

        analyzer = MagicMock()
        analyzer.metrics_for_category.side_effect = ValueError(
            "Invalid category format"
        )
        mock_analyzer_class.return_value = analyzer

        # Execute
        result = category_analysis(category="食費", months=3)

        # Verify Japanese error message
        assert "error" in result
        assert "エラーが発生しました" in result["error"]
        assert "食費" in result["error"]

    @patch("household_mcp.server._get_data_loader")
    @patch("household_mcp.server._data_dir")
    @patch("household_mcp.analysis.trends.CategoryTrendAnalyzer")
    def test_category_analysis_fewer_months_available(
        self, mock_analyzer_class, mock_data_dir, mock_get_loader, mock_analyzer
    ):
        """Test category_analysis when fewer months than requested are available."""
        from household_mcp.server import category_analysis

        # Setup: only 2 months available but user requests 6
        loader = MagicMock()
        loader.iter_available_months.return_value = iter(
            [date(2025, 1, 1), date(2025, 2, 1)]
        )
        mock_get_loader.return_value = loader
        mock_data_dir.return_value = "data"

        # Return only 2 months of data
        mock_analyzer.metrics_for_category.return_value = [
            TrendMetrics(
                category="食費",
                month=date(2025, 2, 1),
                amount=-45000,
                month_over_month=-5.0,
                year_over_year=2.0,
                moving_average=-47000.0,
            ),
            TrendMetrics(
                category="食費",
                month=date(2025, 1, 1),
                amount=-47000,
                month_over_month=8.0,
                year_over_year=3.0,
                moving_average=-46000.0,
            ),
        ]
        mock_analyzer_class.return_value = mock_analyzer

        # Execute: request 6 months but only 2 available
        result = category_analysis(category="食費", months=6)

        # Verify: should return data for only 2 months
        assert "error" not in result
        assert result["months"] == 2  # Adjusted to available months
        assert len(result["monthly_breakdown"]) == 2

    @patch("household_mcp.server._get_data_loader")
    @patch("household_mcp.server._data_dir")
    @patch("household_mcp.analysis.trends.CategoryTrendAnalyzer")
    def test_category_analysis_data_source_error(
        self, mock_analyzer_class, mock_data_dir, mock_get_loader, mock_data_loader
    ):
        """Test category_analysis when DataSourceError is raised."""
        from household_mcp.exceptions import DataSourceError
        from household_mcp.server import category_analysis

        # Setup mocks
        mock_get_loader.return_value = mock_data_loader
        mock_data_dir.return_value = "data"

        analyzer = MagicMock()
        analyzer.metrics_for_category.side_effect = DataSourceError(
            "CSV file is corrupted"
        )
        mock_analyzer_class.return_value = analyzer

        # Execute
        result = category_analysis(category="食費", months=3)

        # Verify Japanese error message
        assert "error" in result
        assert "エラーが発生しました" in result["error"]
        assert "CSV file is corrupted" in result["error"]

    def test_category_analysis_response_structure(self):
        """Test that category_analysis response has the correct structure."""
        from household_mcp.server import category_analysis

        # This is an integration-style test that checks the actual response structure
        # We'll use real data if available, or skip if not
        if not os.path.exists("data"):
            pytest.skip("data directory not available")

        # Execute with real data
        result = category_analysis(category="食費", months=1)

        # Verify structure (regardless of success or error)
        assert isinstance(result, dict)
        assert "category" in result
        assert result["category"] == "食費"

        if "error" not in result:
            # Success case: verify all required fields
            assert "months" in result
            assert "period" in result
            assert "total_expense" in result
            assert "average_expense" in result
            assert "max_month" in result
            assert "min_month" in result
            assert "monthly_breakdown" in result
            assert "summary" in result

            # Verify period structure
            assert "start" in result["period"]
            assert "end" in result["period"]

            # Verify max/min month structure
            for key in ["max_month", "min_month"]:
                assert "year" in result[key]
                assert "month" in result[key]
                assert "amount" in result[key]

            # Verify summary is in Japanese
            assert isinstance(result["summary"], str)
            assert len(result["summary"]) > 0
