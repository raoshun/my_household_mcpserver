"""
Budget management tools (TASK-1403).

This module provides budget management functionality:
- Set budgets for categories and months
- Get current budget status and comparison
- Track budget vs actual spending
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func

from ..database.manager import DatabaseManager
from ..database.models import Budget, Transaction
from ..exceptions import DataSourceError

logger = logging.getLogger(__name__)

_db_manager = DatabaseManager()


def _get_session():
    """Get a database session."""
    return _db_manager.get_session()


def _get_month_expense_by_category(year: int, month: int, category_major: str) -> float:
    """
    Get total expense for a specific month and category.

    Args:
        year: Year
        month: Month (1-12)
        category_major: Major category

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
                Transaction.category_major == category_major,
                Transaction.amount < 0,  # Expenses only
            )
            .scalar()
        )
        return float(result) if result else 0.0
    finally:
        session.close()


def set_budget(
    year: int,
    month: int,
    category_major: str,
    amount: float,
    category_minor: str | None = None,
) -> dict[str, Any]:
    """
    Set or update budget for a category and month.

    Args:
        year: Year
        month: Month (1-12)
        category_major: Major category
        amount: Budget amount (must be positive)
        category_minor: Minor category (optional)

    Returns:
        Dict with operation status and budget details.

    Raises:
        DataSourceError: If amount is negative or validation fails.

    """
    if amount < 0:
        raise DataSourceError("Budget amount must be non-negative")

    if month < 1 or month > 12:
        raise DataSourceError("Month must be between 1 and 12")

    session = _get_session()
    try:
        # Check if budget already exists
        existing = (
            session.query(Budget)
            .filter(
                Budget.year == year,
                Budget.month == month,
                Budget.category_major == category_major,
                Budget.category_minor == category_minor,
            )
            .first()
        )

        if existing:
            # Update existing budget
            existing.amount = amount
            session.commit()
            return {
                "status": "updated",
                "year": year,
                "month": month,
                "category": category_major,
                "category_minor": category_minor,
                "amount": float(amount),
            }
        else:
            # Create new budget
            budget = Budget(
                year=year,
                month=month,
                category_major=category_major,
                category_minor=category_minor,
                amount=amount,
            )
            session.add(budget)
            session.commit()
            return {
                "status": "created",
                "year": year,
                "month": month,
                "category": category_major,
                "category_minor": category_minor,
                "amount": float(amount),
            }
    except Exception as e:
        logger.error(f"Error setting budget: {e}")
        raise DataSourceError(f"Failed to set budget: {e}")
    finally:
        session.close()


def get_budget_status(year: int, month: int, category_major: str) -> dict[str, Any]:
    """
    Get budget status and actual spending comparison.

    Args:
        year: Year
        month: Month (1-12)
        category_major: Major category

    Returns:
        Dict with budget, actual, difference, and achievement rate.

    Raises:
        DataSourceError: If budget not found.

    """
    session = _get_session()
    try:
        # Get budget
        budget = (
            session.query(Budget)
            .filter(
                Budget.year == year,
                Budget.month == month,
                Budget.category_major == category_major,
            )
            .first()
        )

        if not budget:
            raise DataSourceError(
                f"Budget not found for {year}-{month:02d}, {category_major}"
            )

        # Get actual spending
        actual = _get_month_expense_by_category(year, month, category_major)

        # Calculate metrics
        difference = float(budget.amount) - actual
        achievement_rate = (
            (actual / float(budget.amount) * 100) if float(budget.amount) > 0 else 0.0
        )
        is_over_budget = actual > float(budget.amount)

        return {
            "year": year,
            "month": month,
            "category": category_major,
            "budget_amount": float(budget.amount),
            "actual_amount": actual,
            "difference": difference,
            "achievement_rate_pct": round(achievement_rate, 2),
            "is_over_budget": is_over_budget,
            "remaining": max(0.0, difference),
            "overage": max(0.0, -difference),
        }
    finally:
        session.close()


def get_budget_summary(year: int, month: int) -> dict[str, Any]:
    """
    Get summary of all budgets for a month.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Dict with total budget, actual, and category breakdown.

    """
    session = _get_session()
    try:
        # Get all budgets for the month
        budgets = (
            session.query(Budget)
            .filter(
                Budget.year == year,
                Budget.month == month,
            )
            .all()
        )

        if not budgets:
            return {
                "year": year,
                "month": month,
                "total_budget": 0.0,
                "total_actual": 0.0,
                "categories": [],
            }

        # Calculate totals and category breakdown
        total_budget = 0.0
        total_actual = 0.0
        categories = []

        for budget in budgets:
            actual = _get_month_expense_by_category(year, month, budget.category_major)
            budget_amt = float(budget.amount)
            total_budget += budget_amt
            total_actual += actual

            achievement_rate = (actual / budget_amt * 100) if budget_amt > 0 else 0.0

            categories.append(
                {
                    "category": budget.category_major,
                    "budget": budget_amt,
                    "actual": actual,
                    "achievement_rate_pct": round(achievement_rate, 2),
                    "difference": budget_amt - actual,
                    "is_over_budget": actual > budget_amt,
                }
            )

        # Sort by category name
        categories.sort(key=lambda x: x["category"])

        return {
            "year": year,
            "month": month,
            "total_budget": total_budget,
            "total_actual": total_actual,
            "total_achievement_rate_pct": round(
                (total_actual / total_budget * 100) if total_budget > 0 else 0.0,
                2,
            ),
            "total_difference": total_budget - total_actual,
            "categories": categories,
        }
    finally:
        session.close()


def compare_budget_actual(year: int, month: int) -> dict[str, Any]:
    """
    Compare budget vs actual for all categories.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Dict with detailed comparison table.

    """
    summary = get_budget_summary(year, month)

    return {
        "period": f"{year}-{month:02d}",
        "comparison_table": summary["categories"],
        "summary": {
            "total_budget": summary["total_budget"],
            "total_actual": summary["total_actual"],
            "total_difference": summary["total_difference"],
            "overall_achievement": summary["total_achievement_rate_pct"],
        },
    }
