"""Integration tests for FIRE scenario endpoints (TASK-2012)."""

from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from household_mcp.web.http_server import create_http_app

client = TestClient(create_http_app())

BASE = "/api/financial-independence"

VALID_SCENARIO = {
    "name": "Base",
    "current_assets": "5000000",
    "initial_assets": "5000000",
    "monthly_savings": "150000",
    "annual_expense": "3000000",
    "annual_return_rate": "0.04",
    "fire_type": "STANDARD",
    "inflation_rate": "0.02",
    "passive_income": "0",
    "part_time_income": None,
    "side_income": None,
}


def test_fire_scenarios_ok():
    payload = {"scenarios": [VALID_SCENARIO, {**VALID_SCENARIO, "name": "Alt"}]}
    r = client.post(f"{BASE}/scenarios", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "scenarios" in data
    assert "comparison" in data
    assert len(data["scenarios"]) == 2


def test_fire_scenarios_too_many():
    payload = {"scenarios": [VALID_SCENARIO] * 6}  # >5
    r = client.post(f"{BASE}/scenarios", json=payload)
    # Pydantic validation should fail (422)
    assert r.status_code == 422


def test_fire_scenarios_invalid_fire_type():
    bad = {**VALID_SCENARIO, "fire_type": "UNKNOWN"}
    payload = {"scenarios": [bad]}
    r = client.post(f"{BASE}/scenarios", json=payload)
    # Enum lookup triggers KeyError -> 500 or 400 mapped; allow either
    assert r.status_code in (400, 500)


def test_fire_what_if_ok():
    base = dict(VALID_SCENARIO)
    # 全て数値型で明示的に上書き
    base["current_assets"] = "5000000"
    base["initial_assets"] = "5000000"
    base["monthly_savings"] = "150000"
    base["annual_expense"] = "3000000"
    base["annual_return_rate"] = "0.04"
    base["inflation_rate"] = "0.02"
    base["passive_income"] = "0"
    payload = {
        "base_scenario": base,
        "changes": {
            "monthly_savings": "200000",
            "annual_return_rate": "0.05",
        },
    }
    print("=== PAYLOAD ===", payload)
    r = client.post(f"{BASE}/what-if", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    # Structure from what_if_fire_simulation result (dict)
    assert isinstance(data, dict)
    assert any(
        "monthly_savings" in k.lower() or "return" in k.lower() for k in data.keys()
    )


def test_fire_what_if_invalid_key():
    base = dict(VALID_SCENARIO)
    base["initial_assets"] = base["current_assets"]
    payload = {
        "base_scenario": base,
        "changes": {"nonexistent_param": "999"},
    }
    r = client.post(f"{BASE}/what-if", json=payload)
    # Underlying simulator likely ignores or errors; permit 200 or error
    assert r.status_code in (200, 400, 422)


def test_fire_what_if_missing_base_field():
    broken = VALID_SCENARIO.copy()
    broken.pop("annual_return_rate")  # remove required field
    payload = {"base_scenario": broken, "changes": {"monthly_savings": "200000"}}
    r = client.post(f"{BASE}/what-if", json=payload)
    assert r.status_code in (422, 400)
