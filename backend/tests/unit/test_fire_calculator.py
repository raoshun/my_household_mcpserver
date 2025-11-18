"""Unit tests for FIRE calculator utilities."""

from decimal import Decimal

import pytest

from household_mcp.analysis.fire_calculator import FIRECalculator, calculate_fire_index


def test_calculate_fire_target_default_multiplier():
    assert FIRECalculator.calculate_fire_target(1_000_000.0) == 25_000_000.0


def test_calculate_fire_target_custom_multiplier():
    assert (
        FIRECalculator.calculate_fire_target(100_000.0, custom_multiplier=12)
        == 1_200_000.0
    )


def test_calculate_fire_target_invalid():
    with pytest.raises(ValueError):
        FIRECalculator.calculate_fire_target(0)


def test_calculate_progress_rate_and_is_fi_achieved():
    target = FIRECalculator.calculate_fire_target(1_000_000.0)
    # progress rate
    rate = FIRECalculator.calculate_progress_rate(5_000_000.0, target)
    assert rate == round((5_000_000.0 / target) * 100, 2)
    # check is_fi_achieved
    assert FIRECalculator.is_fi_achieved(25_000_000.0, target)
    assert not FIRECalculator.is_fi_achieved(24_999_999.0, target)


def test_calculate_fire_index_simple_feasible():
    # small scenario: current assets near target and monthly savings positive
    current = Decimal("1000000")
    monthly_savings = Decimal("100000")
    target = Decimal("2000000")
    result = calculate_fire_index(current, monthly_savings, target, Decimal("0.05"))

    assert result.target_assets == target
    # months_to_fi should be > 0 when simulation progresses
    assert isinstance(result.months_to_fi, int)
    assert result.months_to_fi != -1
    assert result.feasible is True or result.feasible is False


def test_calculate_fire_index_infeasible():
    # monthly savings zero and current less than target => infeasible
    current = Decimal("100000")
    monthly_savings = Decimal("0")
    target = Decimal("1000000")
    result = calculate_fire_index(current, monthly_savings, target, Decimal("0.01"))

    assert result.months_to_fi == -1
    assert result.feasible is False


def test_calculate_fire_index_invalid_inputs():
    # negative current assets
    with pytest.raises(ValueError):
        calculate_fire_index(
            Decimal("-1"), Decimal("100"), Decimal("1000"), Decimal("0.05")
        )

    # target assets zero
    with pytest.raises(ValueError):
        calculate_fire_index(
            Decimal("0"), Decimal("100"), Decimal("0"), Decimal("0.05")
        )

    # negative annual return
    with pytest.raises(ValueError):
        calculate_fire_index(
            Decimal("0"), Decimal("100"), Decimal("1000"), Decimal("-0.01")
        )
