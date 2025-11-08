"""
Report generation and export tools for household budget data.

Provides functionality to generate various reports (CSV, JSON) and export
transaction data with flexible filtering and formatting options.
"""

import csv
import io
import json
from datetime import datetime
from typing import Any, Literal

from sqlalchemy import desc, extract, func
from sqlalchemy.orm import Session

from household_mcp.database.manager import DatabaseManager
from household_mcp.database.models import Budget, Transaction


def _get_direction(amount: Any) -> str:
    """Get direction from amount sign."""
    amount_float = float(amount)
    return "income" if amount_float > 0 else "expense"


def _get_session() -> Session:
    """Get database session."""
    return DatabaseManager().get_session()


def _format_transaction_row(
    transaction: Transaction,
) -> dict[str, Any]:
    """Format a transaction for report output."""
    return {
        "date": (transaction.date.isoformat() if transaction.date else ""),
        "direction": _get_direction(transaction.amount),
        "category_major": transaction.category_major or "",
        "category_minor": transaction.category_minor or "",
        "description": transaction.description or "",
        "amount": float(abs(transaction.amount)),
        "source": transaction.source_file,
    }


def export_transactions(
    year: int,
    month: int,
    category_major: str | None = None,
    category_minor: str | None = None,
    format: Literal["csv", "json"] = "csv",
) -> str:
    """
    Export transactions with filtering to CSV or JSON format.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
        category_major: Optional major category filter
        category_minor: Optional minor category filter
        format: Output format ('csv' or 'json')

    Returns:
        String content in requested format

    Raises:
        ValueError: If month is not in range 1-12

    """
    if not 1 <= month <= 12:
        raise ValueError(f"Month must be 1-12, got {month}")

    session = _get_session()
    try:
        # Build query with date filters
        query = session.query(Transaction).filter(
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )

        if category_major:
            query = query.filter(Transaction.category_major == category_major)

        if category_minor:
            query = query.filter(Transaction.category_minor == category_minor)

        # Order by date and then by ID for consistency
        transactions = query.order_by(Transaction.date, Transaction.id).all()

        if format == "json":
            return json.dumps(
                {
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "year": year,
                        "month": month,
                        "category_major": category_major,
                        "category_minor": category_minor,
                        "total_records": len(transactions),
                    },
                    "transactions": [_format_transaction_row(t) for t in transactions],
                },
                ensure_ascii=False,
                indent=2,
            )

        # CSV format
        output = io.StringIO()
        if transactions:
            fieldnames = [
                "date",
                "direction",
                "category_major",
                "category_minor",
                "description",
                "amount",
                "source",
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            for transaction in transactions:
                writer.writerow(_format_transaction_row(transaction))

        return output.getvalue()

    finally:
        session.close()


def generate_report(
    year: int,
    month: int,
    report_type: Literal["summary", "detailed", "category"] = "summary",
) -> str:
    """
    Generate analytics report in JSON format.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
        report_type: Type of report
            - 'summary': Income, expense, savings overview
            - 'detailed': Category breakdown with subcategories
            - 'category': Top categories analysis

    Returns:
        JSON string containing the report

    Raises:
        ValueError: If month is not in range 1-12

    """
    if not 1 <= month <= 12:
        raise ValueError(f"Month must be 1-12, got {month}")

    session = _get_session()
    try:
        # Base query for the month
        base_query = session.query(Transaction).filter(
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )

        if report_type == "summary":
            return _generate_summary_report(session, year, month, base_query)
        elif report_type == "detailed":
            return _generate_detailed_report(session, year, month, base_query)
        elif report_type == "category":
            return _generate_category_report(session, year, month, base_query)
        else:
            raise ValueError(f"Unknown report type: {report_type}")

    finally:
        session.close()


def _generate_summary_report(
    session: Session,
    year: int,
    month: int,
    base_query: Any,
) -> str:
    """Generate summary report (income, expense, savings)."""
    # Calculate income (positive amounts)
    income = (
        base_query.filter(Transaction.amount > 0)
        .with_entities(func.sum(Transaction.amount))
        .scalar()
        or 0
    )

    # Calculate expense (negative amounts)
    expense = (
        base_query.filter(Transaction.amount < 0)
        .with_entities(func.sum(func.abs(Transaction.amount)))
        .scalar()
        or 0
    )

    savings = float(income) - float(expense)

    # Get transaction count
    count = base_query.count()

    # Get budget status if available
    budget_summary = (
        session.query(func.sum(Budget.amount).label("total_budget"))
        .filter(
            Budget.year == year,
            Budget.month == month,
        )
        .first()
    )

    budget_total = float(budget_summary.total_budget or 0) if budget_summary else 0

    savings_rate = (savings / float(income) * 100) if float(income) > 0 else 0

    return json.dumps(
        {
            "report_type": "summary",
            "period": f"{year:04d}-{month:02d}",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "income": float(income),
                "expense": float(expense),
                "savings": float(savings),
                "savings_rate": float(savings_rate),
            },
            "budget": {
                "total_budgeted": budget_total,
                "budget_vs_actual": float(budget_total - float(expense)),
                "achievement_rate": (
                    float(
                        (float(expense) / budget_total * 100) if budget_total > 0 else 0
                    )
                ),
            },
            "statistics": {
                "transaction_count": count,
                "avg_expense": (float(float(expense) / count) if count > 0 else 0),
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def _generate_detailed_report(
    session: Session,
    year: int,
    month: int,
    base_query: Any,
) -> str:
    """Generate detailed report with category breakdown."""
    # Get all transactions
    transactions = base_query.order_by(Transaction.amount.desc()).all()

    # Organize by direction and category
    by_category: dict[str, dict[str, dict[str, list[dict]]]] = {
        "income": {},
        "expense": {},
    }

    for transaction in transactions:
        direction = _get_direction(transaction.amount)
        major = transaction.category_major or "(その他)"

        if major not in by_category[direction]:
            by_category[direction][major] = {}

        minor = transaction.category_minor or "(その他)"
        if minor not in by_category[direction][major]:
            by_category[direction][major][minor] = []

        by_category[direction][major][minor].append(
            _format_transaction_row(transaction)
        )

    # Calculate totals by category
    category_totals: dict[str, dict[str, float]] = {
        "income": {},
        "expense": {},
    }

    for direction in ["income", "expense"]:
        for major, minors in by_category[direction].items():
            category_totals[direction][major] = 0
            for minor_list in minors.values():
                category_totals[direction][major] += sum(
                    t["amount"] for t in minor_list
                )

    return json.dumps(
        {
            "report_type": "detailed",
            "period": f"{year:04d}-{month:02d}",
            "generated_at": datetime.now().isoformat(),
            "by_category": {
                "income": {
                    major: {
                        minor: transactions for minor, transactions in minors.items()
                    }
                    for major, minors in by_category["income"].items()
                },
                "expense": {
                    major: {
                        minor: transactions for minor, transactions in minors.items()
                    }
                    for major, minors in by_category["expense"].items()
                },
            },
            "totals": {
                "income": {
                    major: float(amount)
                    for major, amount in category_totals["income"].items()
                },
                "expense": {
                    major: float(amount)
                    for major, amount in category_totals["expense"].items()
                },
            },
        },
        ensure_ascii=False,
        indent=2,
    )


def _generate_category_report(
    session: Session,
    year: int,
    month: int,
    base_query: Any,
) -> str:
    """Generate category analysis report (top categories)."""
    # Get top expense categories
    top_expenses = (
        base_query.filter(Transaction.amount < 0)
        .with_entities(
            Transaction.category_major,
            func.sum(func.abs(Transaction.amount)).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .group_by(Transaction.category_major)
        .order_by(desc("total"))
        .limit(10)
        .all()
    )

    # Get top income categories
    top_income = (
        base_query.filter(Transaction.amount > 0)
        .with_entities(
            Transaction.category_major,
            func.sum(Transaction.amount).label("total"),
            func.count(Transaction.id).label("count"),
        )
        .group_by(Transaction.category_major)
        .order_by(desc("total"))
        .limit(10)
        .all()
    )

    return json.dumps(
        {
            "report_type": "category",
            "period": f"{year:04d}-{month:02d}",
            "generated_at": datetime.now().isoformat(),
            "top_expenses": [
                {
                    "category": cat,
                    "total": float(total),
                    "transaction_count": count,
                    "average": (float(total / count) if count > 0 else 0),
                }
                for cat, total, count in top_expenses
                if cat
            ],
            "top_income": [
                {
                    "category": cat,
                    "total": float(total),
                    "transaction_count": count,
                    "average": (float(total / count) if count > 0 else 0),
                }
                for cat, total, count in top_income
                if cat
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def create_summary_report(year: int, month: int) -> str:
    """
    Create a comprehensive summary combining all report types.

    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)

    Returns:
        JSON string with all report data

    Raises:
        ValueError: If month is not in range 1-12

    """
    if not 1 <= month <= 12:
        raise ValueError(f"Month must be 1-12, got {month}")

    session = _get_session()
    try:
        # Generate all report types
        summary_json = json.loads(generate_report(year, month, "summary"))
        detailed_json = json.loads(generate_report(year, month, "detailed"))
        category_json = json.loads(generate_report(year, month, "category"))

        # Combine into comprehensive report
        return json.dumps(
            {
                "comprehensive_report": {
                    "period": f"{year:04d}-{month:02d}",
                    "generated_at": datetime.now().isoformat(),
                    "summary": summary_json["summary"],
                    "budget": summary_json["budget"],
                    "statistics": summary_json["statistics"],
                    "category_breakdown": detailed_json["totals"],
                    "top_expenses": category_json["top_expenses"],
                    "top_income": category_json["top_income"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )

    finally:
        session.close()
