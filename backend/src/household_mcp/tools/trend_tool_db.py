"""
MCP tool helpers for category trend analysis (DB version).

This module provides DB-based alternatives to CSV trend analysis tools.
It uses the DatabaseManager for direct SQLite access.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
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


def _get_available_categories() -> list[str]:
    """
    Get available major categories from database.

    Returns:
        List of category_major strings.

    """
    session = _get_session()
    try:
        results = (
            session.query(Transaction.category_major)
            .filter(Transaction.amount < 0)  # Only expenses (negative)
            .distinct()
            .order_by(Transaction.category_major)
            .all()
        )
        return [r[0] for r in results if r[0]]
    finally:
        session.close()


def get_category_trend(
    *,
    category: str | None = None,
    start_year: int | None = None,
    start_month: int | None = None,
    end_year: int | None = None,
    end_month: int | None = None,
    top_n: int = 3,
    default_window: int = 12,
) -> dict[str, Any]:
    """
    Return trend analysis for category from database.

    Args:
        category: Specific category to filter. If None, return top_n.
        start_year: Start year. If None, calculate from default_window.
        start_month: Start month (1-12).
        end_year: End year. If None, use latest available.
        end_month: End month (1-12).
        top_n: Number of top categories to return if category is None.
        default_window: Default months to look back if dates not specified.

    Returns:
        Dict with category info and trend data.

    """
    session = _get_session()
    try:
        # Determine date range
        available_months = _get_available_months()
        if not available_months:
            return {
                "category": category,
                "total_amount": 0,
                "transaction_count": 0,
                "start_month": None,
                "end_month": None,
                "error": "No data available",
            }

        # Use latest available month as end
        if end_year is None or end_month is None:
            end_year, end_month = available_months[0]

        # Calculate start date
        if start_year is None or start_month is None:
            # Go back default_window months
            end_date_obj = datetime(end_year, end_month, 28) + timedelta(days=3)
            end_date_obj = end_date_obj.replace(day=1) - timedelta(days=1)
            start_date_obj = end_date_obj.replace(day=1)

            for _ in range(default_window - 1):
                if start_date_obj.month == 1:
                    start_date_obj = start_date_obj.replace(
                        year=start_date_obj.year - 1, month=12
                    )
                else:
                    start_date_obj = start_date_obj.replace(
                        month=start_date_obj.month - 1
                    )
        else:
            # Use specified dates
            start_date_obj = datetime(start_year, start_month, 1)
            end_date_obj = (
                datetime(end_year, end_month, 28) + timedelta(days=3)
            ).replace(day=1) - timedelta(days=1)

        start_month_str = start_date_obj.strftime("%Y-%m")
        end_month_str = end_date_obj.strftime("%Y-%m")

        # Query by month and category
        query = (
            session.query(
                func.extract("year", Transaction.date).label("year"),
                func.extract("month", Transaction.date).label("month"),
                Transaction.category_major,
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(
                Transaction.date >= start_date_obj,
                Transaction.date <= end_date_obj,
                Transaction.amount < 0,  # Expenses only
            )
            .group_by(
                func.extract("year", Transaction.date),
                func.extract("month", Transaction.date),
                Transaction.category_major,
            )
            .order_by(
                func.extract("year", Transaction.date),
                func.extract("month", Transaction.date),
            )
        )

        # Convert to DataFrame
        df = pd.read_sql(query.statement, session.connection())

        if df.empty:
            return {
                "category": category,
                "total_amount": 0,
                "transaction_count": 0,
                "start_month": start_month_str,
                "end_month": end_month_str,
                "error": "No matching data",
            }

        # Filter by category if specified
        if category:
            df_cat = df[df["category_major"] == category]
            if df_cat.empty:
                raise DataSourceError(f"Category '{category}' not found")

            total_amount = df_cat["total_amount"].sum()
            count = df_cat["count"].sum()

            return {
                "category": category,
                "total_amount": float(total_amount),
                "transaction_count": int(count),
                "start_month": start_month_str,
                "end_month": end_month_str,
            }

        # Top categories
        cat_totals = df.groupby("category_major")["total_amount"].sum()
        top_cats = cat_totals.nsmallest(top_n).index.tolist()

        details = []
        for cat in top_cats:
            if cat:
                df_cat = df[df["category_major"] == cat]
                total_amount = df_cat["total_amount"].sum()
                count = df_cat["count"].sum()

                details.append(
                    {
                        "category": cat,
                        "total_amount": float(total_amount),
                        "transaction_count": int(count),
                    }
                )

        return {
            "category": None,
            "start_month": start_month_str,
            "end_month": end_month_str,
            "top_categories": top_cats,
            "details": details,
        }
    except Exception as e:
        logger.error(f"Error getting category trend: {e}")
        raise DataSourceError(f"Failed to get category trend: {e}")
    finally:
        session.close()


def get_monthly_summary(
    year: int | None = None, month: int | None = None
) -> dict[str, Any]:
    """
    Return monthly summary from database.

    Args:
        year: Year. If None, use latest available.
        month: Month (1-12). If None, use latest available.

    Returns:
        Dict with income, expense, savings, and category breakdown.

    """
    session = _get_session()
    try:
        # Determine date to use
        available_months = _get_available_months()
        if not available_months:
            return {"error": "No data available"}

        if year is None or month is None:
            year, month = available_months[0]

        # Get all transactions for the month
        query = session.query(
            Transaction.category_major,
            func.count(Transaction.id).label("count"),
            func.sum(Transaction.amount).label("total_amount"),
        ).filter(
            func.extract("year", Transaction.date) == year,
            func.extract("month", Transaction.date) == month,
        )

        # Group by category
        query = query.group_by(Transaction.category_major)

        # Convert to DataFrame
        df = pd.read_sql(query.statement, session.connection())

        if df.empty:
            return {
                "year": year,
                "month": month,
                "income": 0,
                "expense": 0,
                "savings": 0,
                "savings_rate": 0.0,
                "categories": [],
            }

        # Categorize
        income = float(df[df["total_amount"] > 0]["total_amount"].sum())
        expense = float(abs(df[df["total_amount"] < 0]["total_amount"].sum()))
        savings = income - expense
        savings_rate = (savings / income * 100) if income > 0 else 0.0

        # By category - as list of dicts
        categories = []
        for _, row in df.iterrows():
            cat = row["category_major"]
            if cat:
                categories.append(
                    {
                        "name": cat,
                        "amount": float(abs(row["total_amount"])),
                        "count": int(row["count"]),
                    }
                )

        return {
            "year": year,
            "month": month,
            "income": income,
            "expense": expense,
            "savings": savings,
            "savings_rate": round(savings_rate, 2),
            "categories": categories,
        }
    except Exception as e:
        logger.error(f"Error getting monthly summary: {e}")
        raise DataSourceError(f"Failed to get monthly summary: {e}")
    finally:
        session.close()
