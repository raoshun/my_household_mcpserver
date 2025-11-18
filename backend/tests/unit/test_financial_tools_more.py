"""Additional unit tests for financial_independence_tools."""

from unittest.mock import Mock

import pandas as pd

from household_mcp.tools import financial_independence_tools as fit


def test_project_financial_independence_with_savings(monkeypatch):
    # Patch analyzer to provide a deterministic growth rate
    mock_analyzer = Mock()
    mock_analyzer.get_status.return_value = {
        "months_to_fi": 120,
        "growth_analysis": {"growth_rate_decimal": 0.01},
    }
    monkeypatch.setattr(fit, "analyzer", mock_analyzer)

    result = fit.project_financial_independence_date(additional_savings_per_month=10000)
    assert "current_scenario" in result
    assert "with_additional_savings" in result


def test_compare_scenarios_returns_list(monkeypatch):
    # Patch analyzer to return deterministic scenarios
    mock_analyzer = Mock()

    class Scenario:
        def __init__(self, name):
            self.scenario_name = name
            self.growth_rate = 0.05
            self.months_to_fi = 120
            self.projected_assets_12m = 1
            self.projected_assets_60m = 2
            self.is_achievable = True

    mock_analyzer.calculate_scenarios.return_value = [Scenario("neutral")]
    monkeypatch.setattr(fit, "analyzer", mock_analyzer)

    out = fit.compare_scenarios(scenario_configs={"my": 0.03})
    assert "scenarios" in out
    assert out["total_scenarios"] >= 1


def test_suggest_improvement_actions_returns_list(monkeypatch):
    # Patch analyzer.suggest_improvements to return sample
    mock_analyzer = Mock()
    mock_analyzer.suggest_improvements.return_value = [
        {
            "priority": "HIGH",
            "type": "reduce",
            "title": "Cut food",
            "description": "Reduce eating out",
            "impact": 10000,
        }
    ]
    monkeypatch.setattr(fit, "analyzer", mock_analyzer)
    out = fit.suggest_improvement_actions(annual_expense=1_000_000)
    assert "suggestions" in out
    assert len(out["suggestions"]) == 1


def test_get_annual_expense_breakdown_success(monkeypatch):
    # Prepare fake months and DataFrame
    monkeypatch.setattr(
        fit.data_loader,
        "iter_available_months",
        lambda: [(2024, 1), (2024, 2)],
    )

    df = pd.DataFrame(
        {
            "金額（円）": [-10000, -20000],
            "年月キー": ["2024-01", "2024-02"],
            "大項目": ["食費", "光熱費"],
        }
    )
    monkeypatch.setattr(fit.data_loader, "load_many", lambda months: df)

    out = fit.get_annual_expense_breakdown(year=2024)
    assert out["status"] == "success"
    assert out["months_count"] == 2


def test_compare_actual_vs_fire_target_no_breakdown(monkeypatch):
    # Patch fire_service to return a deterministic FI progress
    mock_fire_service = Mock()
    mock_fire_service.get_status.return_value = {
        "fi_progress": {
            "annual_expense": 820_000.0,
            "current_assets": 20_500_000.0,
            "fire_target": 20_500_000.0,
            "progress_rate": 100.0,
        }
    }
    monkeypatch.setattr(fit, "fire_service", mock_fire_service)

    # Patch breakdown to simulate no CSV data (error)
    monkeypatch.setattr(
        fit,
        "get_annual_expense_breakdown",
        lambda year=None: {"status": "error", "message": "no data"},
    )

    out = fit.compare_actual_vs_fire_target(period_months=12)
    assert out["status"] == "success"
    assert out["actual_annual_expense"] is None
    assert out["difference"] is None
    assert out["expense_ratio"] is None
    assert out["message"] == "実支出データが取得できませんでした"


def test_compare_actual_vs_fire_target_success(monkeypatch):
    # deterministic FI progress
    mock_fire_service = Mock()
    mock_fire_service.get_status.return_value = {
        "fi_progress": {
            "annual_expense": 820_000.0,
            "current_assets": 20_500_000.0,
            "fire_target": 20_500_000.0,
            "progress_rate": 100.0,
        }
    }
    monkeypatch.setattr(fit, "fire_service", mock_fire_service)

    # Patch breakdown to return actual annual expense
    monkeypatch.setattr(
        fit,
        "get_annual_expense_breakdown",
        lambda year=None: {
            "status": "success",
            "total_annual_expense": 5_160_000,
        },
    )

    out = fit.compare_actual_vs_fire_target(period_months=12)
    assert out["status"] == "success"
    # current_assets = 20_500_000
    # FIRE-based expense = 20_500_000 * 0.04 = 820_000
    assert out["fire_based_expense"] == 820_000
    # difference = actual - fire_based = 5_160_000 - 820_000
    assert out["difference"] == 5_160_000 - 820_000
    expected_ratio = 5_160_000 / 820_000
    assert abs(out["expense_ratio"] - expected_ratio) < 0.01
