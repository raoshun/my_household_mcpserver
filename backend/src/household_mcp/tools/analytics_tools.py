"""
Advanced analytics tools for monthly trends and forecasting (TASK-1402).

This module provides enhanced analytics on top of DB-based trend tools:
- Monthly comparison (vs previous month)
- Year-over-year analysis
- Moving averages
- Expense forecasting
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func

from ..database.manager import DatabaseManager
from ..database.models import Transaction
from ..exceptions import DataSourceError

logger = logging.getLogger(__name__)

_db_manager = DatabaseManager()


def _get_session():
    """Get a database session."""
    return _db_manager.get_session()


def _get_available_months() -> list[tuple[int, int]]:
    """
    Get available (year, month) tuples from database.

    Returns:
        List of (year, month) tuples sorted descending.

    """
    session = _get_session()
    try:
        query = session.query(
            func.extract("year", Transaction.date).label("year"),
            func.extract("month", Transaction.date).label("month"),
        ).distinct()
        results = query.order_by(
            func.extract("year", Transaction.date).desc(),
            func.extract("month", Transaction.date).desc(),
        ).all()
        return [(int(y), int(m)) for y, m in results]
    finally:
        session.close()


def _get_month_expense(year: int, month: int) -> float:
    """
    Get total expense for a specific month.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Total expense amount (positive value).

    """
    session = _get_session()
    try:
        result = (
            session.query(func.sum(func.abs(Transaction.amount)).label("total"))
            .filter(
                func.extract("year", Transaction.date) == year,
                func.extract("month", Transaction.date) == month,
                Transaction.amount < 0,  # Expenses only
            )
            .scalar()
        )
        return float(result) if result else 0.0
    finally:
        session.close()


def _get_month_income(year: int, month: int) -> float:
    """
    Get total income for a specific month.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Total income amount.

    """
    session = _get_session()
    try:
        result = (
            session.query(func.sum(Transaction.amount).label("total"))
            .filter(
                func.extract("year", Transaction.date) == year,
                func.extract("month", Transaction.date) == month,
                Transaction.amount > 0,  # Income only
            )
            .scalar()
        )
        return float(result) if result else 0.0
    finally:
        session.close()


def _prev_month(year: int, month: int) -> tuple[int, int]:
    """Get previous month (year, month)."""
    if month == 1:
        return (year - 1, 12)
    return (year, month - 1)


def _prev_year_same_month(year: int, month: int) -> tuple[int, int]:
    """Get same month in previous year."""
    return (year - 1, month)


def get_monthly_comparison(
    year: int | None = None, month: int | None = None
) -> dict[str, Any]:
    """
    Compare current month with previous month.

    Args:
        year: Target year. If None, use latest.
        month: Target month (1-12). If None, use latest.

    Returns:
        Dict with current month, previous month, and comparison metrics.

    """
    # Determine target month
    available_months = _get_available_months()
    if not available_months:
        raise DataSourceError("No transaction data available")

    if year is None or month is None:
        year, month = available_months[0]

    # Get current month data
    current_expense = _get_month_expense(year, month)
    current_income = _get_month_income(year, month)

    # Get previous month data
    prev_year, prev_month = _prev_month(year, month)
    prev_expense = _get_month_expense(prev_year, prev_month)
    prev_income = _get_month_income(prev_year, prev_month)

    # Calculate differences
    expense_diff = current_expense - prev_expense
    expense_diff_pct = (expense_diff / prev_expense * 100) if prev_expense > 0 else 0.0
    income_diff = current_income - prev_income
    income_diff_pct = (income_diff / prev_income * 100) if prev_income > 0 else 0.0

    return {
        "current_month": f"{year}-{month:02d}",
        "previous_month": f"{prev_year}-{prev_month:02d}",
        "current_expense": current_expense,
        "previous_expense": prev_expense,
        "expense_difference": expense_diff,
        "expense_difference_pct": round(expense_diff_pct, 2),
        "current_income": current_income,
        "previous_income": prev_income,
        "income_difference": income_diff,
        "income_difference_pct": round(income_diff_pct, 2),
    }


def get_yoy_comparison(
    year: int | None = None, month: int | None = None
) -> dict[str, Any]:
    """
    Compare current month with same month in previous year (YoY).

    Args:
        year: Target year. If None, use latest.
        month: Target month (1-12). If None, use latest.

    Returns:
        Dict with YoY comparison metrics.

    """
    # Determine target month
    available_months = _get_available_months()
    if not available_months:
        raise DataSourceError("No transaction data available")

    if year is None or month is None:
        year, month = available_months[0]

    # Get current year data
    current_expense = _get_month_expense(year, month)
    current_income = _get_month_income(year, month)

    # Get previous year same month data
    prev_year, _ = _prev_year_same_month(year, month)
    prev_expense = _get_month_expense(prev_year, month)
    prev_income = _get_month_income(prev_year, month)

    # Calculate differences
    expense_diff = current_expense - prev_expense
    expense_diff_pct = (expense_diff / prev_expense * 100) if prev_expense > 0 else 0.0
    income_diff = current_income - prev_income
    income_diff_pct = (income_diff / prev_income * 100) if prev_income > 0 else 0.0

    return {
        "current_year": year,
        "previous_year": prev_year,
        "month": month,
        "current_expense": current_expense,
        "previous_expense": prev_expense,
        "expense_difference": expense_diff,
        "expense_difference_pct": round(expense_diff_pct, 2),
        "current_income": current_income,
        "previous_income": prev_income,
        "income_difference": income_diff,
        "income_difference_pct": round(income_diff_pct, 2),
    }


def get_moving_average(
    months: int = 12, year: int | None = None, month: int | None = None
) -> dict[str, Any]:
    """
    Calculate N-month moving average for expenses.

    Args:
        months: Number of months for moving average (default 12).
        year: End year. If None, use latest.
        month: End month (1-12). If None, use latest.

    Returns:
        Dict with moving average and monthly breakdown.

    """
    if months < 1 or months > 24:
        raise DataSourceError("Moving average months must be between 1 and 24")

    # Determine end month
    available_months = _get_available_months()
    if not available_months:
        raise DataSourceError("No transaction data available")

    if year is None or month is None:
        year, month = available_months[0]

    # Collect monthly expenses
    monthly_data = []
    current_year, current_month = year, month

    for _ in range(months):
        expense = _get_month_expense(current_year, current_month)
        monthly_data.append(
            {
                "month": f"{current_year}-{current_month:02d}",
                "expense": expense,
            }
        )

        # Move to previous month
        current_year, current_month = _prev_month(current_year, current_month)

    # Reverse to chronological order
    monthly_data.reverse()

    # Calculate average
    expenses = [d["expense"] for d in monthly_data]
    average_expense = sum(expenses) / len(expenses)

    return {
        "period_months": months,
        "end_month": f"{year}-{month:02d}",
        "moving_average": round(average_expense, 2),
        "monthly_breakdown": monthly_data,
        "min_expense": min(expenses),
        "max_expense": max(expenses),
        "std_dev": round(
            (sum((x - average_expense) ** 2 for x in expenses) / len(expenses)) ** 0.5,
            2,
        ),
    }


def predict_expense(
    year: int | None = None, month: int | None = None
) -> dict[str, Any]:
    """
    Predict next month's expense based on last 3 months average.

    Args:
        year: Base year. If None, use latest.
        month: Base month (1-12). If None, use latest.

    Returns:
        Dict with prediction and confidence metrics.

    """
    # Determine base month
    available_months = _get_available_months()
    if not available_months:
        raise DataSourceError("No transaction data available")

    if year is None or month is None:
        year, month = available_months[0]

    # Get last 3 months of data
    base_data = []
    current_year, current_month = year, month

    for _ in range(3):
        expense = _get_month_expense(current_year, current_month)
        base_data.append(expense)
        current_year, current_month = _prev_month(current_year, current_month)

    base_data.reverse()

    # Calculate average
    avg_expense = sum(base_data) / 3

    # Calculate trend
    trend = base_data[-1] - base_data[0]  # Latest - Oldest
    trend_pct = (trend / base_data[0] * 100) if base_data[0] > 0 else 0.0

    # Calculate volatility (coefficient of variation)
    mean = avg_expense
    variance = sum((x - mean) ** 2 for x in base_data) / 3
    std_dev = variance**0.5
    cv = (std_dev / mean) if mean > 0 else 0.0  # Coefficient of variation

    # Predict next month (simple: use average with trend consideration)
    predicted_expense = avg_expense + (trend * 0.5)  # Add half the trend

    # Confidence score (lower CV = higher confidence)
    confidence = max(0.0, 1.0 - cv)

    # Get next month
    next_year, next_month = _prev_month(year, month)
    next_year, next_month = _prev_month(next_year, next_month)
    next_year, next_month = _prev_month(next_year, next_month)
    next_year, next_month = _prev_month(next_year, next_month)
    # Move forward 1 month
    if next_month == 12:
        next_year, next_month = next_year + 1, 1
    else:
        next_month = next_month + 1

    return {
        "base_month": f"{year}-{month:02d}",
        "prediction_month": f"{next_year}-{next_month:02d}",
        "last_3_months": base_data,
        "average_expense": round(avg_expense, 2),
        "trend": round(trend, 2),
        "trend_pct": round(trend_pct, 2),
        "predicted_expense": round(predicted_expense, 2),
        "confidence_score": round(confidence, 3),
        "confidence_reason": (
            "High volatility detected"
            if cv > 0.3
            else "Moderate volatility"
            if cv > 0.15
            else "Stable spending pattern"
        ),
    }
