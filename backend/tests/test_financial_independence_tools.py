"""Tests for financial_independence_tools MCP functions.

Focus: validate returned keys and basic types.
"""

from typing import Any

from household_mcp.tools.financial_independence_tools import (
    compare_scenarios,
    get_financial_independence_status,
    project_financial_independence_date,
    suggest_improvement_actions,
)


def _assert_keys(data: dict[str, Any], keys: list[str]) -> None:
    for k in keys:
        assert k in data, f"missing key: {k}"


class TestFinancialIndependenceTools:
    def test_get_financial_independence_status_basic(self) -> None:
        resp = get_financial_independence_status(period_months=6)
        _assert_keys(
            resp,
            [
                "message",
                "progress_rate",
                "fire_target",
                "current_assets",
                "annual_expense",
                "months_to_fi",
                "years_to_fi",
                "is_achieved",
                "snapshot_date",
                "is_interpolated",
                "details",
            ],
        )
        assert isinstance(resp["progress_rate"], (int, float))

    def test_project_financial_independence_date_improvement(self) -> None:
        resp = project_financial_independence_date(additional_savings_per_month=50000)
        _assert_keys(
            resp,
            [
                "message",
                "current_scenario",
                "with_additional_savings",
                "improvement",
            ],
        )
        improvement = resp["improvement"]
        assert improvement["months_saved"] is not None

    def test_suggest_improvement_actions(self) -> None:
        resp = suggest_improvement_actions(annual_expense=900000)
        _assert_keys(resp, ["message", "suggestions"])
        assert isinstance(resp["suggestions"], list)
        if resp["suggestions"]:
            item = resp["suggestions"][0]
            assert "priority" in item and "impact" in item

    def test_compare_scenarios_default(self) -> None:
        resp = compare_scenarios()
        _assert_keys(
            resp,
            ["message", "scenarios", "best_scenario", "total_scenarios"],
        )
        assert isinstance(resp["scenarios"], list)
        assert resp["total_scenarios"] == len(resp["scenarios"])
