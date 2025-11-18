"""Unit tests for FIRE snapshot service.

Focus: interpolation and FI cache recalculation.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock

from household_mcp.database.manager import DatabaseManager
from household_mcp.database.models import FireAssetSnapshot
from household_mcp.services.fire_snapshot import (
    FireSnapshotRequest,
    FireSnapshotService,
    LinearSnapshotInterpolator,
    SnapshotPoint,
)

# pytest fixtures (tmp_path, monkeypatch) are available implicitly


def test_linear_snapshot_interpolation_midpoint() -> None:
    interp = LinearSnapshotInterpolator()

    p1 = SnapshotPoint(
        snapshot_date=date(2024, 1, 1),
        values={
            "cash_and_deposits": 100,
            "stocks_cash": 200,
            "investment_trusts": 300,
            "pension": 0,
            "stocks_margin": 0,
            "points": 0,
        },
    )
    p2 = SnapshotPoint(
        snapshot_date=date(2024, 2, 1),
        values={
            "cash_and_deposits": 200,
            "stocks_cash": 400,
            "investment_trusts": 600,
            "pension": 0,
            "stocks_margin": 0,
            "points": 0,
        },
    )

    out = interp.interpolate(date(2024, 1, 16), [p1, p2])

    # Compute expected using same ratio calculation as the interpolator
    span = (p2.snapshot_date - p1.snapshot_date).days
    offset = (date(2024, 1, 16) - p1.snapshot_date).days
    ratio = offset / span

    expected_cash = round(
        p1.values["cash_and_deposits"]
        + (p2.values["cash_and_deposits"] - p1.values["cash_and_deposits"]) * ratio
    )
    expected_stocks = round(
        p1.values["stocks_cash"]
        + (p2.values["stocks_cash"] - p1.values["stocks_cash"]) * ratio
    )
    expected_trusts = round(
        p1.values["investment_trusts"]
        + (p2.values["investment_trusts"] - p1.values["investment_trusts"]) * ratio
    )

    assert out["cash_and_deposits"] == expected_cash
    assert out["stocks_cash"] == expected_stocks
    assert out["investment_trusts"] == expected_trusts


def _create_db_manager(tmp_path) -> DatabaseManager:
    db_path = tmp_path / "test.db"
    db = DatabaseManager(db_path=str(db_path))
    db.initialize_database()
    return db


def test_register_snapshot_updates_fi_cache(tmp_path):
    """Registering a snapshot should create FireAssetSnapshot and FIProgressCache.

    The FinancialIndependenceAnalyzer is patched so the returned metrics are
    deterministic and we can assert they are stored in the cache.
    """
    db = _create_db_manager(tmp_path)

    mock_analyzer = Mock()
    mock_analyzer.get_status.return_value = {
        "fire_target": 1_000_000,
        "progress_rate": 50.0,
        "growth_analysis": {
            "growth_rate_decimal": 0.03,
            "confidence": 0.8,
            "data_points": 7,
        },
        "months_to_fi": 120,
    }

    # Create service with our mock analyzer so we don't rely on heavy logic
    svc = FireSnapshotService(db, analyzer=mock_analyzer)

    # Register a snapshot
    req = FireSnapshotRequest(
        snapshot_date=date(2024, 1, 1),
        cash_and_deposits=1_000_000,
        stocks_cash=0,
        stocks_margin=0,
        investment_trusts=0,
        pension=0,
        points=0,
        notes="unit test",
    )

    resp = svc.register_snapshot(req)
    assert resp.total == 1_000_000

    # Verify snapshot persisted and cache created
    with db.session_scope() as session:
        snap = (
            session.query(FireAssetSnapshot)
            .filter_by(snapshot_date=req.snapshot_date)
            .one_or_none()
        )
        assert snap is not None

    status = svc.get_status(snapshot_date=req.snapshot_date, months=1)
    fi = status["fi_progress"]
    assert float(fi["current_assets"]) == float(req.cash_and_deposits)
    assert float(fi["fire_target"]) == float(
        mock_analyzer.get_status.return_value["fire_target"]
    )


def test_recalculate_interpolates_between_snapshots(tmp_path):
    """When snapshot_date is between two stored snapshots we
    should interpolate.
    """
    db = _create_db_manager(tmp_path)

    mock_analyzer = Mock()
    # The analyzer just needs to accept the numbers and return some metrics
    mock_analyzer.get_status.return_value = {
        "fire_target": 1_000_000,
        "progress_rate": 50.0,
        "growth_analysis": {
            "growth_rate_decimal": 0.03,
            "confidence": 0.8,
            "data_points": 7,
        },
        "months_to_fi": 120,
    }

    svc = FireSnapshotService(db, analyzer=mock_analyzer)

    # Add two snapshots (via register_snapshot so the table is populated)
    svc.register_snapshot(
        FireSnapshotRequest(
            snapshot_date=date(2024, 1, 1),
            cash_and_deposits=1000,
            stocks_cash=0,
            stocks_margin=0,
            investment_trusts=0,
            pension=0,
            points=0,
            notes="one",
        )
    )

    svc.register_snapshot(
        FireSnapshotRequest(
            snapshot_date=date(2024, 3, 1),
            cash_and_deposits=3000,
            stocks_cash=0,
            stocks_margin=0,
            investment_trusts=0,
            pension=0,
            points=0,
            notes="three",
        )
    )

    # Recalculate for interim date
    # Use public API to trigger cache recalculation and interpolation
    status = svc.get_status(snapshot_date=date(2024, 2, 1), months=12)

    # Interpolated current assets should match expected linear blend
    fi = status["fi_progress"]
    span = (date(2024, 3, 1) - date(2024, 1, 1)).days
    offset = (date(2024, 2, 1) - date(2024, 1, 1)).days
    expected_assets = round(1000 + (3000 - 1000) * (offset / span), 0)
    assert abs(float(fi["current_assets"]) - float(expected_assets)) < 1


# End of file
