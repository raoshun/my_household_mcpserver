"""Tests for CSV-based annual expense calculation in FireSnapshotService."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, Mock, patch

import pandas as pd
import pytest

from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.services.fire_snapshot import FireSnapshotService

if TYPE_CHECKING:
    from household_mcp.database.manager import DatabaseManager


@pytest.fixture
def mock_db_manager() -> Mock:
    """Create a mock database manager."""
    return Mock()


@pytest.fixture
def mock_data_loader() -> Mock:
    """Create a mock data loader."""
    loader = Mock(spec=HouseholdDataLoader)
    return loader


@pytest.fixture
def fire_service(mock_db_manager: Mock, mock_data_loader: Mock) -> FireSnapshotService:
    """Create FireSnapshotService with mocked dependencies."""
    return FireSnapshotService(mock_db_manager, data_loader=mock_data_loader)


class TestCalculateAnnualExpenseFromCSV:
    """Test _calculate_annual_expense_from_csv method."""

    def test_12_month_csv_calculation(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test calculation with 12 months of CSV data."""
        # Setup: 12 months available
        mock_data_loader.iter_available_months.return_value = [
            (2024, m) for m in range(1, 13)
        ]

        # Mock DataFrame with realistic expense data
        df = pd.DataFrame(
            {
                "金額（円）": [-100000] * 12,  # ¥100k per month
                "計算対象": [1] * 12,
            }
        )
        mock_data_loader.load_many.return_value = df

        # Execute
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 12, 31))

        # Verify
        assert result == 1_200_000.0
        mock_data_loader.load_many.assert_called_once()
        called_months = mock_data_loader.load_many.call_args[0][0]
        assert len(called_months) == 12

    def test_6_month_annualization(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test annualization with only 6 months of data."""
        # Setup: Only 6 months available
        mock_data_loader.iter_available_months.return_value = [
            (2024, m) for m in range(1, 7)
        ]

        # Mock DataFrame with 6 months data
        df = pd.DataFrame(
            {
                "金額（円）": [-50000] * 6,  # ¥50k per month
                "計算対象": [1] * 6,
            }
        )
        mock_data_loader.load_many.return_value = df

        # Execute
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 6, 30))

        # Verify: Should be doubled (annualized)
        assert result == 600_000.0
        mock_data_loader.load_many.assert_called_once()
        called_months = mock_data_loader.load_many.call_args[0][0]
        assert len(called_months) == 6

    def test_insufficient_data_returns_none(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test returns None with insufficient data (< 6 months)."""
        # Setup: Only 3 months available
        mock_data_loader.iter_available_months.return_value = [
            (2024, m) for m in range(1, 4)
        ]

        # Execute
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 3, 31))

        # Verify
        assert result is None

    def test_no_data_available_returns_none(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test returns None when no CSV data available."""
        # Setup: No months available
        mock_data_loader.iter_available_months.return_value = []

        # Execute
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 12, 31))

        # Verify
        assert result is None

    def test_no_data_loader_returns_none(
        self,
        mock_db_manager: Mock,
    ) -> None:
        """Test returns None when data_loader is not provided."""
        # Create service without data_loader
        service = FireSnapshotService(mock_db_manager, data_loader=None)

        # Execute
        result = service._calculate_annual_expense_from_csv(date(2024, 12, 31))

        # Verify
        assert result is None

    def test_filters_months_by_snapshot_date(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test filters months <= snapshot_date."""
        # Setup: 24 months available
        mock_data_loader.iter_available_months.return_value = [
            (2023, m) for m in range(1, 13)
        ] + [(2024, m) for m in range(1, 13)]

        df = pd.DataFrame(
            {
                "金額（円）": [-100000] * 12,
                "計算対象": [1] * 12,
            }
        )
        mock_data_loader.load_many.return_value = df

        # Execute with snapshot_date in middle of 2024
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 6, 30))

        # Verify: Should use last 12 months up to 2024-06
        assert result == 1_200_000.0
        called_months = mock_data_loader.load_many.call_args[0][0]
        assert len(called_months) == 12
        assert called_months[-1] == (2024, 6)

    def test_zero_expense_returns_none(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test returns None when total expense is zero."""
        # Setup: 12 months with zero expenses
        mock_data_loader.iter_available_months.return_value = [
            (2024, m) for m in range(1, 13)
        ]

        df = pd.DataFrame(
            {
                "金額（円）": [0] * 12,
                "計算対象": [1] * 12,
            }
        )
        mock_data_loader.load_many.return_value = df

        # Execute
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 12, 31))

        # Verify
        assert result is None

    def test_handles_negative_amounts_correctly(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test correctly handles negative amounts (expenses in CSV)."""
        # Setup
        mock_data_loader.iter_available_months.return_value = [
            (2024, m) for m in range(1, 13)
        ]

        # Mix of negative values (actual expenses in CSV format)
        df = pd.DataFrame(
            {
                "金額（円）": [-50000, -100000, -75000] * 4,
                "計算対象": [1] * 12,
            }
        )
        mock_data_loader.load_many.return_value = df

        # Execute
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 12, 31))

        # Verify: abs() should be applied
        # Total: abs((-50k - 100k - 75k) * 4) = abs(-900k) = 900k
        assert result == 900_000.0

    def test_exception_handling_returns_none(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test returns None when exception occurs."""
        # Setup: Mock to raise exception
        mock_data_loader.iter_available_months.side_effect = RuntimeError(
            "Database error"
        )

        # Execute
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 12, 31))

        # Verify: Should catch exception and return None
        assert result is None

    def test_prefers_12_month_over_6_month(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test prefers 12-month calculation when both 6 and 12 months available."""
        # Setup: 18 months available
        mock_data_loader.iter_available_months.return_value = [
            (2023, m) for m in range(7, 13)
        ] + [(2024, m) for m in range(1, 13)]

        df = pd.DataFrame(
            {
                "金額（円）": [-100000] * 12,
                "計算対象": [1] * 12,
            }
        )
        mock_data_loader.load_many.return_value = df

        # Execute
        result = fire_service._calculate_annual_expense_from_csv(date(2024, 12, 31))

        # Verify: Should use 12-month calculation (not 6-month doubled)
        assert result == 1_200_000.0
        called_months = mock_data_loader.load_many.call_args[0][0]
        assert len(called_months) == 12


class TestEstimateAnnualExpenseWithCSV:
    """Test _estimate_annual_expense with CSV integration."""

    def test_priority_csv_over_asset_based(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test CSV calculation takes priority over asset-based estimation."""
        # Setup: CSV data available
        mock_data_loader.iter_available_months.return_value = [
            (2024, m) for m in range(1, 13)
        ]

        df = pd.DataFrame(
            {
                "金額（円）": [-200000] * 12,  # ¥2.4M per year
                "計算対象": [1] * 12,
            }
        )
        mock_data_loader.load_many.return_value = df

        # Asset history would suggest different value (¥5M * 4% = ¥200k)
        asset_history = [5_000_000.0]

        # Execute
        result = fire_service._estimate_annual_expense(
            asset_history, snapshot_date=date(2024, 12, 31)
        )

        # Verify: Should use CSV value, not asset-based
        assert result == 2_400_000.0

    def test_fallback_to_asset_based_when_csv_unavailable(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test falls back to asset-based when CSV returns None."""
        # Setup: CSV returns None (insufficient data)
        mock_data_loader.iter_available_months.return_value = []

        # Asset history available
        asset_history = [5_000_000.0]

        # Execute
        result = fire_service._estimate_annual_expense(
            asset_history, snapshot_date=date(2024, 12, 31)
        )

        # Verify: Should use asset-based (4% rule)
        assert result == 200_000.0  # 5M * 0.04

    def test_fallback_to_default_when_no_data(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test falls back to default when no CSV or asset data."""
        # Setup: No CSV data
        mock_data_loader.iter_available_months.return_value = []

        # No asset history
        asset_history: list[float] = []

        # Execute
        result = fire_service._estimate_annual_expense(
            asset_history, snapshot_date=date(2024, 12, 31)
        )

        # Verify: Should use default value
        assert result == 1_200_000.0  # default_annual_expense

    def test_no_snapshot_date_skips_csv_calculation(
        self,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
    ) -> None:
        """Test skips CSV calculation when snapshot_date is None."""
        # Setup: CSV data available but snapshot_date is None
        mock_data_loader.iter_available_months.return_value = [
            (2024, m) for m in range(1, 13)
        ]

        asset_history = [5_000_000.0]

        # Execute without snapshot_date
        result = fire_service._estimate_annual_expense(
            asset_history, snapshot_date=None
        )

        # Verify: Should skip CSV and use asset-based
        assert result == 200_000.0
        mock_data_loader.iter_available_months.assert_not_called()


class TestRecalculateFICacheIntegration:
    """Test _recalculate_fi_cache with CSV integration."""

    @patch("household_mcp.services.fire_snapshot.FIRECalculator")
    @patch("household_mcp.services.fire_snapshot.FinancialIndependenceAnalyzer")
    def test_passes_snapshot_date_to_expense_estimation(
        self,
        mock_analyzer_class: Mock,
        mock_calculator_class: Mock,
        fire_service: FireSnapshotService,
        mock_data_loader: Mock,
        mock_db_manager: Mock,
    ) -> None:
        """Test _recalculate_fi_cache passes snapshot_date correctly."""
        # Setup mocks
        mock_session = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_session)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_db_manager.session_scope = MagicMock(return_value=mock_context)

        # Mock snapshot points
        mock_snapshot = MagicMock()
        mock_snapshot.snapshot_date = date(2024, 12, 31)
        mock_snapshot.cash_and_deposits = 1000000
        mock_snapshot.stocks_cash = 0
        mock_snapshot.stocks_margin = 0
        mock_snapshot.investment_trusts = 0
        mock_snapshot.pension = 0
        mock_snapshot.points = 0

        mock_query = MagicMock()
        mock_query.order_by.return_value.all.return_value = [mock_snapshot]
        mock_query.order_by.return_value.filter.return_value.one_or_none.return_value = (
            None
        )
        mock_session.query.return_value = mock_query

        # Mock CSV data
        mock_data_loader.iter_available_months.return_value = [
            (2024, m) for m in range(1, 13)
        ]
        df = pd.DataFrame(
            {
                "金額（円）": [-100000] * 12,
                "計算対象": [1] * 12,
            }
        )
        mock_data_loader.load_many.return_value = df

        # Mock analyzer and calculator
        mock_analyzer = Mock()
        mock_analyzer.get_status.return_value = {
            "fire_target": 30_000_000.0,
            "progress_rate": 3.3,
            "growth_analysis": {
                "growth_rate_decimal": 0.01,
                "confidence": 0.8,
                "data_points": 12,
            },
            "months_to_fi": 240,
        }
        fire_service.analyzer = mock_analyzer

        mock_calculator_class.calculate_fire_target.return_value = 30_000_000.0

        # Execute: Call with snapshot_date
        fire_service._recalculate_fi_cache(mock_session, date(2024, 12, 31))

        # Verify: CSV calculation should be called
        mock_data_loader.load_many.assert_called_once()
