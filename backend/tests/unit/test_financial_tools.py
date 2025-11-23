"""Unit tests for `tools/financial_independence_tools.py`."""

import pytest

from household_mcp.services.fire_snapshot import SnapshotNotFoundError
from household_mcp.tools import financial_independence_tools as fit


def test_submit_asset_record_valid():
    result = fit.submit_asset_record(2024, 3, "cash", 100000)
    assert result["status"] == "success"
    assert result["record"]["year"] == 2024


def test_submit_asset_record_invalid_month():
    result = fit.submit_asset_record(2024, 13, "cash", 100000)
    assert result["status"] == "error"


def test_submit_asset_record_negative_amount():
    result = fit.submit_asset_record(2024, 3, "cash", -1000)
    assert result["status"] == "error"


def test_submit_asset_record_invalid_type():
    result = fit.submit_asset_record(2024, 3, "gold", 1000)
    assert result["status"] == "error"


def test_get_financial_independence_status_no_snapshots(monkeypatch):
    monkeypatch.setattr(fit, "fire_service", fit.fire_service)

    def _raise(snapshot_date=None, months=12, recalculate=False):
        raise SnapshotNotFoundError()

    monkeypatch.setattr(fit.fire_service, "get_status", _raise)

    status = fit.get_financial_independence_status(period_months=12)
    assert status["progress_rate"] == 0.0
    assert status["current_assets"] == 0


def test_get_annual_expense_breakdown_no_data(monkeypatch):
    monkeypatch.setattr(fit.data_loader, "iter_available_months", lambda: [])
    out = fit.get_annual_expense_breakdown(year=None)
    assert out["status"] == "error"
