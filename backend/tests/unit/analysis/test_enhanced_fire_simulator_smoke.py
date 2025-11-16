"""Lightweight coverage tests for FIRE APIs (TASK-2017)."""

from fastapi.testclient import TestClient

from household_mcp.web.http_server import create_http_app

client = TestClient(create_http_app())

BASE = "/api/financial-independence"


def _make_scenario(fire_type: str, annual_expense: str = "2400000"):
    """Helper to create valid scenario dict."""
    current_assets = "5000000"
    return {
        "name": "Test",
        "fire_type": fire_type,
        "current_assets": current_assets,
        "initial_assets": current_assets,  # Required field
        "monthly_savings": "100000",
        "annual_expense": annual_expense,
        "annual_return_rate": "0.04",
        "inflation_rate": "0.02",
        "passive_income": "0",
    }


def test_standard_fire_coverage():
    """Coverage: STANDARD FIRE scenario."""
    response = client.post(
        f"{BASE}/scenarios",
        json={"scenarios": [_make_scenario("STANDARD")]},
    )
    assert response.status_code == 200


def test_coast_fire_coverage():
    """Coverage: COAST FIRE scenario."""
    response = client.post(
        f"{BASE}/scenarios",
        json={"scenarios": [_make_scenario("COAST")]},
    )
    assert response.status_code == 200


def test_barista_fire_coverage():
    """Coverage: BARISTA FIRE scenario."""
    scenario = _make_scenario("BARISTA")
    scenario["part_time_income"] = "50000"
    response = client.post(
        f"{BASE}/scenarios",
        json={"scenarios": [scenario]},
    )
    assert response.status_code == 200


def test_side_fire_coverage():
    """Coverage: SIDE FIRE scenario."""
    scenario = _make_scenario("SIDE", "3600000")
    scenario["side_income"] = "80000"
    response = client.post(
        f"{BASE}/scenarios",
        json={"scenarios": [scenario]},
    )
    assert response.status_code == 200


def test_what_if_monthly_savings():
    """Coverage: what-if simulation with monthly_savings change."""
    response = client.post(
        f"{BASE}/what-if",
        json={
            "base_scenario": _make_scenario("STANDARD"),
            "changes": {"monthly_savings": "150000"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    # API returns snake_case keys: monthly_savings_before/after
    assert "monthly_savings_before" in data
    assert "monthly_savings_after" in data
    assert "impact" in data


def test_what_if_annual_return_rate():
    """Coverage: what-if simulation with annual_return_rate change."""
    response = client.post(
        f"{BASE}/what-if",
        json={
            "base_scenario": _make_scenario("STANDARD"),
            "changes": {"annual_return_rate": "0.06"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    # API returns snake_case keys: annual_return_rate_before/after
    assert "annual_return_rate_before" in data
    assert "annual_return_rate_after" in data
    assert "impact" in data
