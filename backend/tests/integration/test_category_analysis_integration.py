"""Integration tests for category_analysis tool with real data."""

import os
import sys

import pytest

# Import directly from the actual server module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from household_mcp import server  # noqa: E402


class TestCategoryAnalysisIntegration:
    """Integration tests for category_analysis using real CSV data."""

    def test_category_analysis_with_real_data(self) -> None:
        """Test category_analysis with actual CSV files."""
        if not os.path.exists("data"):
            pytest.skip("data directory not available")

        # Test with a common category
        result = server.category_analysis(category="食費", months=3)

        # Should either return data or a meaningful error
        assert isinstance(result, dict)
        assert "category" in result
        assert result["category"] == "食費"

        if "error" in result:
            # If error, it should be in Japanese
            error_msg = result["error"]
            assert isinstance(error_msg, str)
            assert len(error_msg) > 0
            # Typical error messages
            assert any(
                keyword in error_msg
                for keyword in [
                    "データが利用できません",
                    "データが見つかりませんでした",
                    "エラーが発生しました",
                ]
            )
        else:
            # If successful, verify structure
            assert "months" in result
            assert "period" in result
            assert "total_expense" in result
            assert "average_expense" in result
            assert "monthly_breakdown" in result
            assert "summary" in result

            # Verify data types
            assert isinstance(result["months"], int)
            assert result["months"] > 0
            assert isinstance(result["total_expense"], int)
            assert isinstance(result["average_expense"], int)
            assert isinstance(result["monthly_breakdown"], list)
            assert isinstance(result["summary"], str)

            # Verify summary contains Japanese text
            assert len(result["summary"]) > 0
            assert "食費" in result["summary"]
            assert "円" in result["summary"]

    def test_category_analysis_nonexistent_category(self) -> None:
        """Test category_analysis with a category that doesn't exist."""
        if not os.path.exists("data"):
            pytest.skip("data directory not available")

        result = server.category_analysis(category="存在しないカテゴリXYZ", months=3)

        # Should return an error
        assert isinstance(result, dict)
        assert "category" in result
        assert result["category"] == "存在しないカテゴリXYZ"

        # Error message should be in Japanese
        if "error" in result:
            error_msg = result["error"]
            assert isinstance(error_msg, str)
            # Should indicate data not found
            assert (
                "データが見つかりません" in error_msg
                or "データが利用できません" in error_msg
            )

    def test_category_analysis_default_months(self) -> None:
        """Test category_analysis with default months parameter."""
        if not os.path.exists("data"):
            pytest.skip("data directory not available")

        # Should use default of 3 months
        result = server.category_analysis(category="食費")

        assert isinstance(result, dict)
        assert "category" in result

        if "error" not in result:
            # Default months should be applied
            assert "months" in result
            assert result["months"] <= 3  # May be less if fewer months available

    def test_category_analysis_large_month_range(self) -> None:
        """Test category_analysis with a large month range."""
        if not os.path.exists("data"):
            pytest.skip("data directory not available")

        # Request 12 months (may get fewer)
        result = server.category_analysis(category="食費", months=12)

        assert isinstance(result, dict)
        assert "category" in result

        if "error" not in result:
            assert "months" in result
            assert result["months"] <= 12  # Should not exceed available data
            assert result["months"] > 0

    def test_category_analysis_japanese_error_messages(self) -> None:
        """Verify all error messages are in Japanese."""
        if not os.path.exists("data"):
            pytest.skip("data directory not available")

        # Test various scenarios that might produce errors
        test_cases = [
            {"category": "存在しないカテゴリ", "months": 3},
            {"category": "", "months": 3},  # Empty category
            {"category": "テスト", "months": 100},  # Too many months
        ]

        for test_case in test_cases:
            result = server.category_analysis(**test_case)

            # If there's an error, it should be in Japanese
            if "error" in result:
                error_msg = result["error"]
                assert isinstance(error_msg, str)
                assert len(error_msg) > 0

                # Should contain Japanese characters or typical Japanese error keywords
                japanese_keywords = [
                    "データ",
                    "エラー",
                    "見つかりませ",
                    "利用できません",
                    "発生しました",
                    "ディレクトリ",
                    "CSV",
                    "ファイル",
                ]
                assert any(
                    keyword in error_msg for keyword in japanese_keywords
                ), f"Error message not in Japanese: {error_msg}"

    def test_category_analysis_response_format(self) -> None:
        """Test that the response follows the expected format."""
        if not os.path.exists("data"):
            pytest.skip("data directory not available")

        result = server.category_analysis(category="食費", months=1)

        # Basic structure check
        assert isinstance(result, dict)
        assert "category" in result

        if "error" not in result:
            # Success response structure
            required_fields = [
                "category",
                "months",
                "period",
                "total_expense",
                "average_expense",
                "max_month",
                "min_month",
                "monthly_breakdown",
                "summary",
            ]

            for field in required_fields:
                assert field in result, f"Missing required field: {field}"

            # Period structure
            assert "start" in result["period"]
            assert "end" in result["period"]
            assert isinstance(result["period"]["start"], str)
            assert isinstance(result["period"]["end"], str)

            # Max/min month structure
            for key in ["max_month", "min_month"]:
                assert "year" in result[key]
                assert "month" in result[key]
                assert "amount" in result[key]
                assert isinstance(result[key]["year"], int)
                assert isinstance(result[key]["month"], int)
                assert isinstance(result[key]["amount"], int)

            # Monthly breakdown structure
            assert isinstance(result["monthly_breakdown"], list)
            if len(result["monthly_breakdown"]) > 0:
                month_data = result["monthly_breakdown"][0]
                assert "year" in month_data
                assert "month" in month_data
                assert "amount" in month_data
                assert "mom_change" in month_data
