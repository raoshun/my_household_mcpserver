"""Tests for resources module."""

from unittest.mock import patch

from household_mcp import resources


class TestResourceFunctions:
    """Test suite for resource module functions."""

    def test_data_dir_default(self):
        """Test _data_dir returns default value."""
        with patch.dict("os.environ", {}, clear=True):
            result = resources._data_dir()
            assert result == "data"

    def test_data_dir_from_env(self):
        """Test _data_dir returns env variable value."""
        with patch.dict("os.environ", {"HOUSEHOLD_DATA_DIR": "/custom/path"}):
            result = resources._data_dir()
            assert result == "/custom/path"

    def test_get_data_loader_singleton(self):
        """Test data loader is singleton."""
        resources._data_loader = None  # Reset
        loader1 = resources._get_data_loader()
        loader2 = resources._get_data_loader()
        assert loader1 is loader2

    @patch("household_mcp.resources._get_data_loader")
    def test_get_category_hierarchy_success(self, mock_loader):
        """Test get_category_hierarchy with valid data."""
        mock_loader.return_value.category_hierarchy.return_value = {
            "食費": ["外食", "食材"],
            "交通費": ["電車", "タクシー"],
        }

        result = resources.get_category_hierarchy()

        assert isinstance(result, dict)
        assert "食費" in result
        assert len(result["食費"]) == 2

    @patch("household_mcp.resources._get_data_loader")
    def test_get_category_hierarchy_data_source_error(self, mock_loader):
        """Test get_category_hierarchy handles DataSourceError."""
        from household_mcp.exceptions import DataSourceError

        mock_loader.return_value.category_hierarchy.side_effect = DataSourceError(
            "No data"
        )

        result = resources.get_category_hierarchy()

        assert result == {}

    @patch("household_mcp.resources._get_data_loader")
    def test_get_available_months_success(self, mock_loader):
        """Test get_available_months with valid data."""
        mock_loader.return_value.iter_available_months.return_value = [
            (2024, 1),
            (2024, 2),
            (2024, 3),
        ]

        result = resources.get_available_months()

        assert len(result) == 3
        assert result[0] == {"year": 2024, "month": 1}
        assert result[2] == {"year": 2024, "month": 3}

    @patch("household_mcp.resources._get_data_loader")
    def test_get_available_months_data_source_error(self, mock_loader):
        """Test get_available_months handles DataSourceError."""
        from household_mcp.exceptions import DataSourceError

        mock_loader.return_value.iter_available_months.side_effect = DataSourceError(
            "No data"
        )

        result = resources.get_available_months()

        assert result == []

    @patch("household_mcp.resources._get_data_loader")
    def test_get_household_categories_success(self, mock_loader):
        """Test get_household_categories with valid data."""
        mock_loader.return_value.category_hierarchy.return_value = {
            "住宅": ["家賃", "光熱費"]
        }

        result = resources.get_household_categories()

        assert isinstance(result, dict)
        assert "住宅" in result

    @patch("household_mcp.resources.category_trend_summary")
    @patch("household_mcp.resources._data_dir")
    def test_get_category_trend_summary_success(
        self, mock_data_dir, mock_trend_summary
    ):
        """Test get_category_trend_summary with valid data."""
        mock_data_dir.return_value = "data"
        mock_trend_summary.return_value = {"食費": {"total": 50000, "count": 10}}

        result = resources.get_category_trend_summary()

        assert isinstance(result, dict)
        assert "食費" in result

    @patch("household_mcp.resources.category_trend_summary")
    @patch("household_mcp.resources._data_dir")
    def test_get_category_trend_summary_data_source_error(
        self, mock_data_dir, mock_trend_summary
    ):
        """Test get_category_trend_summary handles DataSourceError."""
        from household_mcp.exceptions import DataSourceError

        mock_data_dir.return_value = "data"
        mock_trend_summary.side_effect = DataSourceError("No data")

        result = resources.get_category_trend_summary()

        assert result == {"summary": {}}

    def test_get_transactions_no_report_tools(self):
        """Test get_transactions when report tools unavailable."""
        original = resources.HAS_REPORT_TOOLS
        resources.HAS_REPORT_TOOLS = False

        result = resources.get_transactions()

        assert "error" in result
        assert "not available" in result["error"]

        resources.HAS_REPORT_TOOLS = original

    def test_get_monthly_summary_resource_no_report_tools(self):
        """Test get_monthly_summary_resource when report tools unavailable."""
        original = resources.HAS_REPORT_TOOLS
        resources.HAS_REPORT_TOOLS = False

        result = resources.get_monthly_summary_resource()

        assert "error" in result

        resources.HAS_REPORT_TOOLS = original

    def test_get_budget_status_resource_no_report_tools(self):
        """Test get_budget_status_resource when report tools unavailable."""
        original = resources.HAS_REPORT_TOOLS
        resources.HAS_REPORT_TOOLS = False

        result = resources.get_budget_status_resource()

        assert "error" in result

        resources.HAS_REPORT_TOOLS = original
