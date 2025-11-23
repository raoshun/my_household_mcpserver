"""Tests for financial_independence_tools MCP functions.

Focus: validate returned keys and basic types.
"""

from datetime import date
from decimal import Decimal
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd

from household_mcp.tools.financial_independence_tools import (
    analyze_expense_patterns,
    compare_scenarios,
    get_financial_independence_status,
    project_financial_independence_date,
    suggest_improvement_actions,
)


def _assert_keys(data: dict[str, Any], keys: list[str]) -> None:
    for k in keys:
        assert k in data, f"missing key: {k}"


@patch("household_mcp.tools.financial_independence_tools.fire_service")
@patch("household_mcp.tools.financial_independence_tools.data_loader")
@patch("household_mcp.tools.financial_independence_tools.analyzer")
@patch("household_mcp.tools.financial_independence_tools.pattern_analyzer")
class TestFinancialIndependenceTools:
    def test_get_financial_independence_status_basic(
        self, mock_pattern, mock_analyzer, mock_loader, mock_fire
    ) -> None:
        mock_fire.get_status.return_value = {
            "snapshot": {
                "total": 1000000,
                "snapshot_date": date(2023, 1, 1),
                "is_interpolated": False,
            },
            "fi_progress": {
                "annual_expense": 1200000,
                "progress_rate": 10.0,
                "fire_target": 30000000,
                "monthly_growth_rate": 0.004,
                "months_to_fi": 120,
                "is_achievable": True,
            },
        }

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

    def test_project_financial_independence_date_improvement(
        self, mock_pattern, mock_analyzer, mock_loader, mock_fire
    ) -> None:
        mock_fire.get_status.return_value = {
            "snapshot": {"total": 1000000},
            "fi_progress": {
                "fire_target": 30000000,
                "monthly_growth_rate": 0.004,
                "months_to_fi": 120,
            },
        }

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

    def test_suggest_improvement_actions(
        self, mock_pattern, mock_analyzer, mock_loader, mock_fire
    ) -> None:
        mock_fire.get_status.return_value = {
            "snapshot": {"total": 1000000},
            "fi_progress": {"annual_expense": 1200000},
        }
        # Empty DF for basic test
        mock_loader.load_many.return_value = pd.DataFrame()
        mock_analyzer.classify_expenses.return_value = {}
        mock_analyzer.suggest_improvements.return_value = [
            {
                "priority": "HIGH",
                "type": "reduction",
                "title": "Reduce Food",
                "description": "Eat less",
                "impact": 10000,
            }
        ]

        resp = suggest_improvement_actions(annual_expense=900000)
        _assert_keys(resp, ["message", "suggestions"])
        assert isinstance(resp["suggestions"], list)
        if resp["suggestions"]:
            item = resp["suggestions"][0]
            assert "priority" in item and "impact" in item

    def test_compare_scenarios_default(
        self, mock_pattern, mock_analyzer, mock_loader, mock_fire
    ) -> None:
        resp = compare_scenarios()
        _assert_keys(
            resp,
            ["message", "scenarios", "best_scenario", "total_scenarios"],
        )
        assert isinstance(resp["scenarios"], list)
        assert resp["total_scenarios"] == len(resp["scenarios"])

    def test_analyze_expense_patterns_mocked(
        self, mock_pattern, mock_analyzer, mock_loader, mock_fire
    ) -> None:
        # Mock _get_target_months to control date range
        with patch(
            "household_mcp.tools.financial_independence_tools._get_target_months"
        ) as mock_get_months:
            mock_get_months.return_value = [(2023, 1), (2023, 2)]

            # Setup mock data loader
            mock_df = pd.DataFrame(
                {
                    "年月": [
                        pd.Timestamp("2023-01-01"),
                        pd.Timestamp("2023-02-01"),
                    ],
                    "カテゴリ": ["食費", "食費"],
                    "金額（円）": [-1000, -2000],
                    "計算対象": [1, 1],
                }
            )
            mock_loader.load_many.return_value = mock_df

            # Setup mock pattern analyzer
            mock_result = MagicMock()
            mock_classification = MagicMock()
            mock_classification.category = "食費"
            mock_classification.classification = "regular"
            mock_classification.average_amount = Decimal("1500")
            mock_result.classifications = [mock_classification]
            mock_pattern.analyze_expenses.return_value = mock_result

            result = analyze_expense_patterns(period_months=2)

            assert result["regular_spending"] == 3000.0
            assert len(result["categories"]) == 1
            assert result["categories"][0]["category"] == "食費"
            assert result["categories"][0]["classification"] == "regular"
