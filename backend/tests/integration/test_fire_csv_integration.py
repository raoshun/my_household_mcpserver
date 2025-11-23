"""Integration tests for CSV-based FIRE calculations with MCP tools."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from household_mcp.database.manager import DatabaseManager
from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.services.fire_snapshot import (
    FireSnapshotRequest,
    FireSnapshotService,
)
from household_mcp.tools.financial_independence_tools import (
    compare_actual_vs_fire_target,
    get_annual_expense_breakdown,
)

# No typing-only imports required in this test module


@pytest.fixture
def temp_csv_data(tmp_path: Path) -> Path:
    """Create temporary CSV data for testing."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create 12 months of test data
    import calendar

    for month in range(1, 13):
        end_day = calendar.monthrange(2024, month)[1]
        filename = (
            f"収入・支出詳細_2024-{month:02d}-01_2024-{month:02d}-{end_day:02d}.csv"
        )
        df = pd.DataFrame(
            {
                "計算対象": [1] * 10,
                "金額（円）": [-100000, -50000, -30000, -20000, -15000] * 2,
                "日付": [f"2024-{month:02d}-{day:02d}" for day in range(1, 11)],
                "内容": ["テスト支出"] * 10,
                "保有金融機関": ["テスト銀行"] * 10,
                "大項目": ["食費", "交通費", "住宅", "光熱費", "通信費"] * 2,
                "中項目": ["外食", "電車", "家賃", "電気", "携帯"] * 2,
                "メモ": [""] * 10,
                "振替": [0] * 10,
                "ID": list(range(month * 100, month * 100 + 10)),
            }
        )
        df.to_csv(data_dir / filename, index=False, encoding="cp932")

    return data_dir


@pytest.fixture
def db_manager_with_snapshot(tmp_path: Path) -> DatabaseManager:
    """Create DatabaseManager with test snapshot data."""
    db_path = tmp_path / "test.db"
    db_manager = DatabaseManager(db_path=str(db_path))
    db_manager.initialize_database()

    # Create snapshot
    fire_service = FireSnapshotService(db_manager)
    request = FireSnapshotRequest(
        snapshot_date=pd.Timestamp("2024-12-31").date(),
        cash_and_deposits=10_000_000,
        stocks_cash=5_000_000,
        stocks_margin=0,
        investment_trusts=3_000_000,
        pension=2_000_000,
        points=500_000,
        notes="Test snapshot",
    )
    fire_service.register_snapshot(request)

    return db_manager


class TestCSVBasedFIRECalculation:
    """Integration tests for CSV-based FIRE calculations."""

    def test_fire_service_with_csv_data(
        self,
        temp_csv_data: Path,
        db_manager_with_snapshot: DatabaseManager,
    ) -> None:
        """Test FireSnapshotService calculates from CSV data."""
        # Setup
        data_loader = HouseholdDataLoader(src_dir=temp_csv_data)
        fire_service = FireSnapshotService(
            db_manager_with_snapshot, data_loader=data_loader
        )

        # Ensure FI cache is recalculated using CSV-based loader before
        # checking (the fixture created a cache with asset-based values).
        # status (the fixture created a cache entry using an asset-only
        # FireSnapshotService instance - we need to refresh it with CSV data).
        with db_manager_with_snapshot.session_scope() as session:
            fire_service._recalculate_fi_cache(
                session, pd.Timestamp("2024-12-31").date()
            )

        # Execute
        status = fire_service.get_status(snapshot_date=None, months=12)

        # Verify
        assert "fi_progress" in status
        fi_progress = status["fi_progress"]

        # Annual expense should be calculated from CSV
        # 12 months * (100k + 50k + 30k + 20k + 15k) * 2 =
        # 12 * 215k * 2 = 5,160,000
        # The CSV test data includes two sets of expense rows per month.
        # Each month sums to ¥430,000 (absolute), therefore annual = 430k * 12
        expected_annual = 5_160_000.0
        assert fi_progress["annual_expense"] == expected_annual

        # FIRE target should be annual_expense * 25
        assert fi_progress["fire_target"] == expected_annual * 25

        # Current assets = 20,500,000
        assert fi_progress["current_assets"] == 20_500_000.0

        # Progress rate
        expected_progress = (20_500_000.0 / (expected_annual * 25)) * 100
        assert abs(fi_progress["progress_rate"] - expected_progress) < 0.1

    def test_get_annual_expense_breakdown(
        self,
        temp_csv_data: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test get_annual_expense_breakdown MCP tool."""
        # Setup: Patch the global data_loader
        from household_mcp.tools import financial_independence_tools

        data_loader = HouseholdDataLoader(src_dir=temp_csv_data)
        monkeypatch.setattr(financial_independence_tools, "data_loader", data_loader)

        # Ensure we are using monthly CSVs before executing the tool
        result = get_annual_expense_breakdown(year=2024)

        # Verify
        assert result["status"] == "success"
        assert result["total_annual_expense"] == 5_160_000
        assert result["months_count"] == 12

        # Check monthly breakdown
        monthly = result["monthly_breakdown"]
        assert len(monthly) == 12
        for month_data in monthly:
            assert month_data["amount"] == 430_000  # Per month

        # Check category breakdown
        categories = result["category_breakdown"]
        assert len(categories) == 5
        category_names = {cat["category"] for cat in categories}
        assert category_names == {"食費", "交通費", "住宅", "光熱費", "通信費"}

    def test_compare_actual_vs_fire_target_integration(
        self,
        temp_csv_data: Path,
        db_manager_with_snapshot: DatabaseManager,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test compare_actual_vs_fire_target with real data."""
        # Setup
        from household_mcp.tools import financial_independence_tools

        data_loader = HouseholdDataLoader(src_dir=temp_csv_data)
        fire_service = FireSnapshotService(
            db_manager_with_snapshot, data_loader=data_loader
        )

        monkeypatch.setattr(financial_independence_tools, "data_loader", data_loader)
        monkeypatch.setattr(financial_independence_tools, "fire_service", fire_service)

        # Execute
        result = compare_actual_vs_fire_target(period_months=12)

        # Verify
        assert result["status"] == "success"
        assert result["actual_annual_expense"] == 5_160_000

        # Current assets = 20,500,000
        # FIRE-based expense (4%) = 20,500,000 * 0.04 = 820,000
        assert result["fire_based_expense"] == 820_000

        # Difference versus FIRE-based expense
        assert result["difference"] == 5_160_000 - 820_000

        # Ratio
        expected_ratio = 5_160_000 / 820_000
        assert abs(result["expense_ratio"] - expected_ratio) < 0.01

    def test_fire_progress_without_csv_fallback(
        self,
        db_manager_with_snapshot: DatabaseManager,
    ) -> None:
        """Test FIRE calculation falls back to asset-based without CSV."""
        # Setup: No data_loader (CSV unavailable)
        fire_service = FireSnapshotService(db_manager_with_snapshot, data_loader=None)

        # Execute
        status = fire_service.get_status(snapshot_date=None, months=12)

        # Verify
        fi_progress = status["fi_progress"]

        # Should use asset-based calculation (4% rule)
        # Current assets = 20,500,000
        # Annual expense = 20,500,000 * 0.04 = 820,000
        assert fi_progress["annual_expense"] == 820_000.0

        # FIRE target = 820,000 * 25 = 20,500,000
        assert fi_progress["fire_target"] == 20_500_000.0

        # Progress should be 100% (current = target)
        assert abs(fi_progress["progress_rate"] - 100.0) < 0.1

    def test_csv_with_partial_year_data(
        self,
        tmp_path: Path,
        db_manager_with_snapshot: DatabaseManager,
    ) -> None:
        """Test CSV calculation with only 6 months (annualization)."""
        # Setup: Only 6 months of data
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        import calendar

        for month in range(1, 7):
            end_day = calendar.monthrange(2024, month)[1]
            filename = (
                f"収入・支出詳細_2024-{month:02d}-01_2024-{month:02d}-{end_day:02d}.csv"
            )
            df = pd.DataFrame(
                {
                    "計算対象": [1] * 10,
                    "金額（円）": [-100000] * 10,
                    "日付": [f"2024-{month:02d}-{day:02d}" for day in range(1, 11)],
                    "内容": ["テスト"] * 10,
                    "保有金融機関": ["テスト"] * 10,
                    "大項目": ["食費"] * 10,
                    "中項目": ["外食"] * 10,
                    "メモ": [""] * 10,
                    "振替": [0] * 10,
                    "ID": list(range(month * 100, month * 100 + 10)),
                }
            )
            df.to_csv(data_dir / filename, index=False, encoding="cp932")

        data_loader = HouseholdDataLoader(src_dir=data_dir)
        fire_service = FireSnapshotService(
            db_manager_with_snapshot, data_loader=data_loader
        )
        # Force recalculation with CSV-derived annualization
        with db_manager_with_snapshot.session_scope() as session:
            fire_service._recalculate_fi_cache(
                session, pd.Timestamp("2024-06-30").date()
            )

        # Execute
        status = fire_service.get_status(snapshot_date=None, months=12)

        # Verify: Should be annualized (6 months * 2)
        # 6 months * 10 records * 100k = 6,000,000
        # Annualized = 6,000,000 * 2 = 12,000,000
        # The direct CSV calculation should produce the expected annualized
        # value (12 months equivalent of 6 months of data)
        csv_annual = fire_service._calculate_annual_expense_from_csv(
            pd.Timestamp("2024-06-30").date()
        )
        assert csv_annual == 12_000_000.0

    def test_estimate_annual_expense_from_csv(
        self,
        temp_csv_data: Path,
        db_manager_with_snapshot: DatabaseManager,
    ) -> None:
        """Test estimate_annual_expense calculates correctly from CSV."""
        data_loader = HouseholdDataLoader(src_dir=temp_csv_data)
        fire_service = FireSnapshotService(
            db_manager_with_snapshot, data_loader=data_loader
        )

        # Calculate for 2024-12-31 (all 12 months available)
        expense = fire_service.estimate_annual_expense(
            snapshot_date=pd.Timestamp("2024-12-31").date()
        )

        # Expected: 430,000 * 12 = 5,160,000
        # Each month has 10 records: [-100000, -50000, -30000, -20000, -15000] * 2
        # Sum per month = 430,000
        assert expense == 5_160_000.0

    def test_get_financial_independence_status_tool_integration(
        self,
        temp_csv_data: Path,
        db_manager_with_snapshot: DatabaseManager,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test get_financial_independence_status tool integration."""
        from household_mcp.tools import financial_independence_tools

        # Setup dependencies
        data_loader = HouseholdDataLoader(src_dir=temp_csv_data)
        fire_service = FireSnapshotService(
            db_manager_with_snapshot, data_loader=data_loader
        )

        monkeypatch.setattr(financial_independence_tools, "data_loader", data_loader)
        monkeypatch.setattr(financial_independence_tools, "fire_service", fire_service)

        # Execute tool
        result = financial_independence_tools.get_financial_independence_status(
            period_months=12
        )

        # Verify
        assert result["annual_expense"] == 5_160_000
        assert result["fire_target"] == 5_160_000 * 25
        assert result["current_assets"] == 20_500_000
        # Progress: 20.5M / 129M = ~15.8%
        expected_progress = (20_500_000 / (5_160_000 * 25)) * 100
        assert abs(result["progress_rate"] - expected_progress) < 0.1

    def test_get_financial_independence_status_no_snapshot(
        self,
        temp_csv_data: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test tool behavior when no snapshots exist but CSV data is available."""
        from household_mcp.tools import financial_independence_tools

        # Setup: Empty database (no snapshots)
        db_path = tmp_path / "empty.db"
        db_manager = DatabaseManager(db_path=str(db_path))
        db_manager.initialize_database()

        data_loader = HouseholdDataLoader(src_dir=temp_csv_data)
        fire_service = FireSnapshotService(db_manager, data_loader=data_loader)

        monkeypatch.setattr(financial_independence_tools, "data_loader", data_loader)
        monkeypatch.setattr(financial_independence_tools, "fire_service", fire_service)

        # Execute tool
        result = financial_independence_tools.get_financial_independence_status(
            period_months=12
        )

        # Verify
        # Should calculate annual expense from CSV even without snapshots
        assert result["annual_expense"] == 5_160_000
        assert result["fire_target"] == 5_160_000 * 25

        # Assets should be 0 as no snapshot exists
        assert result["current_assets"] == 0
        assert result["progress_rate"] == 0.0
        assert result["months_to_fi"] is None
