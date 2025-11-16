"""Integration tests for income analysis endpoints (TASK-2012)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from household_mcp.web.http_server import create_http_app

client = TestClient(create_http_app())

# Existing data years appear to include 2022-2025 (per data directory listing)
EXISTING_YEAR = 2022
EXISTING_MONTH = 1


def test_get_monthly_income_ok():
    url = f"/api/v1/income/{EXISTING_YEAR}/{EXISTING_MONTH}"
    r = client.get(url)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("year") == EXISTING_YEAR
    assert data.get("month") == EXISTING_MONTH
    assert "total_income" in data


def test_get_monthly_income_invalid_month():
    url = f"/api/v1/income/{EXISTING_YEAR}/13"  # invalid month
    r = client.get(url)
    # FastAPI validation should yield 422
    assert r.status_code == 422


def test_get_annual_income_ok():
    url = f"/api/v1/income/{EXISTING_YEAR}"
    r = client.get(url)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("year") == EXISTING_YEAR
    assert "total_income" in data
    assert "category_breakdown" in data


def test_get_annual_income_invalid_year():
    url = "/api/v1/income/1999"  # below Path constraint ge=2000
    r = client.get(url)
    assert r.status_code == 422


def test_get_monthly_savings_rate_ok():
    url = f"/api/v1/savings-rate/{EXISTING_YEAR}/{EXISTING_MONTH}"
    r = client.get(url)
    assert r.status_code == 200, r.text
    data = r.json()
    for key in ["year", "month", "savings_rate", "income", "expense"]:
        assert key in data


def test_get_monthly_savings_rate_invalid_month():
    url = f"/api/v1/savings-rate/{EXISTING_YEAR}/0"  # invalid month
    r = client.get(url)
    assert r.status_code == 422


def test_get_savings_rate_trend_ok():
    # Endpoint requires start_date/end_date
    params = {
        "start_date": f"{EXISTING_YEAR}-01-01",
        "end_date": f"{EXISTING_YEAR}-03-31",
    }
    r = client.get("/api/v1/savings-rate/trend", params=params)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("start_date") == f"{EXISTING_YEAR}-01-01"
    assert data.get("end_date") == f"{EXISTING_YEAR}-03-31"
    assert isinstance(data.get("trend"), list)


def test_get_real_estate_cashflow_ok():
    params = {
        "start_date": f"{EXISTING_YEAR}-01-01",
        "end_date": f"{EXISTING_YEAR}-01-31",
    }
    r = client.get("/api/v1/real-estate-cashflow", params=params)
    assert r.status_code == 200, r.text
    data = r.json()
    # Actual tool returns aggregated numeric metrics; ensure key presence
    for key in ["income", "expense", "net_cashflow"]:
        assert key in data


def test_get_real_estate_cashflow_bad_date():
    params = {
        "start_date": "2022-01-XX",
        "end_date": f"{EXISTING_YEAR}-01-31",
    }
    r = client.get("/api/v1/real-estate-cashflow", params=params)
    # Expect 400 from ValueError in tools
    assert r.status_code in (400, 422)


def test_get_cashflow_report_ok():
    r = client.get(f"/api/v1/cashflow-report/{EXISTING_YEAR}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("format") in {"markdown", "json"}
    assert "content" in data


def test_get_cashflow_report_invalid_year():
    r = client.get("/api/v1/cashflow-report/1999")
    assert r.status_code == 422
