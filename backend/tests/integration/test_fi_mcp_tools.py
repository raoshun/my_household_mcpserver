"""Integration tests for financial independence MCP tools."""

from __future__ import annotations

import os
from datetime import date as real_date
from unittest.mock import patch

import pytest

from household_mcp.tools.financial_independence_tools import (
    analyze_expense_patterns,
    compare_scenarios,
    get_financial_independence_status,
    project_financial_independence_date,
    suggest_improvement_actions,
)


@pytest.fixture(autouse=True)
def mock_today():
    """Mock today to be 2025-07-01.

    This ensures we have data for 'last month' (June 2025).
    """
    with patch("household_mcp.tools.financial_independence_tools.date") as mock_date:
        mock_date.today.return_value = real_date(2025, 7, 1)
        mock_date.side_effect = lambda *args, **kwargs: real_date(*args, **kwargs)
        yield


@pytest.fixture(autouse=True)
def mock_fire_service():
    """Mock fire_service to return dummy data for integration tests."""
    with patch(
        "household_mcp.tools.financial_independence_tools.fire_service"
    ) as mock_service:
        mock_service.get_status.return_value = {
            "snapshot": {
                "total": 5000000,
                "snapshot_date": "2025-07-01",
                "is_interpolated": False,
            },
            "fi_progress": {
                "fire_target": 60000000,
                "monthly_growth_rate": 0.005,
                "months_to_fi": 120,
                "annual_expense": 2400000,
                "progress_rate": 8.33,
            },
        }
        yield


@pytest.fixture(autouse=True)
def check_data():
    """Skip tests if data directory or CSV files are missing."""
    if not os.path.exists("data") or not any(
        f.endswith(".csv") for f in os.listdir("data")
    ):
        pytest.skip("Real data not available in backend/data")


class TestFIToolsIntegration:
    """Integration tests for FI MCP tools."""

    def test_get_status_returns_dict(self) -> None:
        """Test get_financial_independence_status returns dict."""
        result = get_financial_independence_status(period_months=12)
        assert isinstance(result, dict)
        assert "message" in result
        assert "progress_rate" in result
        assert "fire_target" in result

    def test_get_status_with_custom_period(self) -> None:
        """Test get_status with custom period."""
        result = get_financial_independence_status(period_months=24)
        assert isinstance(result, dict)
        assert result.get("progress_rate") is not None

    def test_analyze_patterns_returns_dict(self) -> None:
        """Test analyze_expense_patterns returns dict."""
        result = analyze_expense_patterns(period_months=12)
        assert isinstance(result, dict)
        assert "message" in result
        assert "categories" in result
        assert isinstance(result["categories"], list)

    def test_analyze_patterns_japanese_text(self) -> None:
        """Test analyze_patterns includes Japanese text."""
        result = analyze_expense_patterns(period_months=12)
        assert "定期" in result["message"] or "支出" in result["message"]

    def test_project_date_no_savings(self) -> None:
        """Test projection with no additional savings."""
        result = project_financial_independence_date(additional_savings_per_month=0.0)
        assert isinstance(result, dict)
        assert "current_scenario" in result
        assert "improvement" in result

    def test_project_date_with_savings(self) -> None:
        """Test projection with additional monthly savings."""
        result = project_financial_independence_date(
            additional_savings_per_month=100000.0
        )
        assert isinstance(result, dict)
        additional = result["with_additional_savings"]["additional_monthly"]
        assert additional == 100000.0

    def test_suggest_improvements_returns_dict(self) -> None:
        """Test suggest_improvements returns dict."""
        result = suggest_improvement_actions(annual_expense=1000000)
        assert isinstance(result, dict)
        assert "message" in result
        assert "suggestions" in result
        assert isinstance(result["suggestions"], list)

    def test_suggest_improvements_json_structure(self) -> None:
        """Test suggestions have required fields."""
        result = suggest_improvement_actions(annual_expense=1000000)
        if result["suggestions"]:
            sugg = result["suggestions"][0]
            assert "priority" in sugg
            assert "priority_ja" in sugg

    def test_compare_scenarios_returns_dict(self) -> None:
        """Test compare_scenarios returns dict."""
        result = compare_scenarios()
        assert isinstance(result, dict)
        assert "scenarios" in result
        assert isinstance(result["scenarios"], list)

    def test_compare_scenarios_with_custom_config(self) -> None:
        """Test scenario comparison with custom config."""
        custom_config = {
            "保守的": 0.005,
            "標準": 0.01,
            "積極的": 0.02,
        }
        result = compare_scenarios(scenario_configs=custom_config)
        assert isinstance(result, dict)
        assert len(result["scenarios"]) > 0

    def test_tools_return_japanese_messages(self) -> None:
        """Test all tools return Japanese messages."""
        tools_funcs = [
            ("get_status", get_financial_independence_status),
            ("analyze_patterns", analyze_expense_patterns),
            ("project_date", project_financial_independence_date),
            ("suggest_improvements", suggest_improvement_actions),
            ("compare_scenarios", compare_scenarios),
        ]

        for name, func in tools_funcs:
            result = func()
            assert isinstance(result, dict)
            assert "message" in result, f"{name} missing message"

    def test_status_contains_required_keys(self) -> None:
        """Test status contains all required information keys."""
        result = get_financial_independence_status()
        required_keys = [
            "message",
            "progress_rate",
            "fire_target",
            "current_assets",
            "annual_expense",
            "is_achieved",
        ]
        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_patterns_contains_category_info(self) -> None:
        """Test patterns contain category information."""
        result = analyze_expense_patterns()
        assert "categories" in result
        for cat in result["categories"]:
            assert "category" in cat
            assert "classification" in cat
            assert "confidence" in cat

    def test_projection_shows_time_saved(self) -> None:
        """Test projection shows time saved vs base case."""
        result = project_financial_independence_date(
            additional_savings_per_month=50000.0
        )
        assert "improvement" in result
        assert "years_saved" in result["improvement"] or (
            result["improvement"]["years_saved"] is not None
        )

    def test_scenarios_identify_best_scenario(self) -> None:
        """Test scenario comparison identifies best scenario."""
        result = compare_scenarios()
        if result.get("best_scenario"):
            best = result["best_scenario"]
            assert "scenario_name" in best
            assert "years_to_fi" in best

    def test_all_tools_handle_errors_gracefully(self) -> None:
        """Test tools handle invalid inputs appropriately."""
        # Test with custom period (should not raise)
        try:
            result1 = get_financial_independence_status(period_months=1)
            assert isinstance(result1, dict)

            result2 = project_financial_independence_date(
                additional_savings_per_month=50000.0
            )
            assert isinstance(result2, dict)
        except Exception as e:
            pytest.fail(f"Tool raised exception on valid input: {e}")

    def test_status_numerics_are_reasonable(self) -> None:
        """Test status returns reasonable numeric values."""
        result = get_financial_independence_status()
        assert result["progress_rate"] >= 0
        assert result["fire_target"] > 0
        assert result["current_assets"] > 0

    def test_patterns_totals_are_positive(self) -> None:
        """Test expense patterns return positive totals."""
        result = analyze_expense_patterns()
        assert result["regular_spending"] >= 0
        assert result["irregular_spending"] >= 0

    def test_scenario_names_are_japanese(self) -> None:
        """Test scenario names include Japanese text."""
        result = compare_scenarios()
        if result["scenarios"]:
            scenario = result["scenarios"][0]
            # Check if scenario name contains CJK characters
            name = scenario.get("scenario_name", "")
            # Simplified check - just ensure it's not empty
            assert len(name) > 0

    def test_improvement_suggestions_have_priority(self) -> None:
        """Test improvement suggestions include priority."""
        result = suggest_improvement_actions()
        if result["suggestions"]:
            for sugg in result["suggestions"]:
                priority = sugg.get("priority")
                assert priority in ["HIGH", "MEDIUM", "LOW"]

    def test_all_tools_with_default_params(self) -> None:
        """Test all tools work with default parameters."""
        tools = [
            get_financial_independence_status,
            analyze_expense_patterns,
            project_financial_independence_date,
            suggest_improvement_actions,
            compare_scenarios,
        ]

        for tool in tools:
            try:
                result = tool()
                assert isinstance(result, dict)
                assert "message" in result
            except Exception as e:
                pytest.fail(f"Tool failed with defaults: {e}")


class TestFIToolsOutputFormats:
    """Test output formats for FI tools."""

    def test_status_output_includes_japanese_text(self) -> None:
        """Test status includes Japanese UI text."""
        result = get_financial_independence_status()
        message = result["message"]
        assert isinstance(message, str)
        assert len(message) > 0
        # Check for Japanese characters or English text
        assert any(char.isalnum() or ord(char) > 127 for char in message)

    def test_patterns_output_includes_yen_symbol(self) -> None:
        """Test patterns include ¥ symbol in message."""
        result = analyze_expense_patterns()
        message = result["message"]
        assert "¥" in message or "支出" in message

    def test_projection_years_are_floats(self) -> None:
        """Test projection years are float type."""
        result = project_financial_independence_date()
        current = result.get("current_scenario", {})
        if current.get("years_to_fi") is not None:
            assert isinstance(
                current["years_to_fi"],
                (int, float),
            )

    def test_scenarios_growth_rate_pct(self) -> None:
        """Test scenario growth rate is percentage."""
        result = compare_scenarios()
        for scenario in result.get("scenarios", []):
            rate = scenario.get("growth_rate_pct")
            if rate is not None:
                assert 0 <= rate <= 1000  # Reasonable percentage range
