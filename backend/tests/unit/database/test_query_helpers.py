"""Unit tests for query_helpers.

NOTE: These tests require the 'db' extra (sqlalchemy).
They are skipped automatically when sqlalchemy is unavailable.
"""

# flake8: noqa: F811

from datetime import date, datetime
from decimal import Decimal

import pytest

try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

    from household_mcp.database.models import Base, Transaction
    from household_mcp.database.query_helpers import (
        get_active_transactions,
        get_category_breakdown,
        get_duplicate_impact_report,
        get_monthly_summary,
    )

    HAS_DB = True
except Exception:
    HAS_DB = False
    Session = object

pytestmark = pytest.mark.skipif(not HAS_DB, reason="requires db extras (sqlalchemy)")


@pytest.fixture
def db_session():  # type: ignore[no-untyped-def]
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_transactions(db_session: Session):  # type: ignore[no-untyped-def]
    """Create sample transactions for testing."""
    transactions = [
        # January transactions
        Transaction(
            source_file="test.csv",
            row_number=1,
            date=datetime(2024, 1, 15),
            amount=Decimal("-5000.00"),
            description="食料品",
            category_major="食費",
            category_minor="食料品",
            account="現金",
            is_duplicate=0,
        ),
        Transaction(
            source_file="test.csv",
            row_number=2,
            date=datetime(2024, 1, 15),
            amount=Decimal("-5000.00"),
            description="食料品（重複）",
            category_major="食費",
            category_minor="食料品",
            account="クレジットカード",
            is_duplicate=1,  # Marked as duplicate
            duplicate_of=1,
        ),
        Transaction(
            source_file="test.csv",
            row_number=3,
            date=datetime(2024, 1, 20),
            amount=Decimal("-3000.00"),
            description="交通費",
            category_major="交通費",
            category_minor="電車",
            account="IC カード",
            is_duplicate=0,
        ),
        Transaction(
            source_file="test.csv",
            row_number=4,
            date=datetime(2024, 1, 25),
            amount=Decimal("200000.00"),
            description="給与",
            category_major="収入",
            category_minor="給与",
            account="銀行",
            is_duplicate=0,
        ),
        # February transactions
        Transaction(
            source_file="test.csv",
            row_number=5,
            date=datetime(2024, 2, 10),
            amount=Decimal("-10000.00"),
            description="食料品",
            category_major="食費",
            category_minor="食料品",
            account="現金",
            is_duplicate=0,
        ),
    ]
    for trans in transactions:
        db_session.add(trans)
    db_session.commit()
    return transactions


def test_get_active_transactions_all(db_session: Session, sample_transactions):  # type: ignore[no-untyped-def]
    """Test getting all active transactions."""
    transactions = get_active_transactions(db_session, exclude_duplicates=True)

    assert len(transactions) == 4  # 5 total - 1 duplicate
    assert all(t.is_duplicate == 0 for t in transactions)


def test_get_active_transactions_with_duplicates(  # type: ignore[no-untyped-def]
    db_session: Session, sample_transactions
):
    """Test getting transactions including duplicates."""
    transactions = get_active_transactions(db_session, exclude_duplicates=False)

    assert len(transactions) == 5  # All transactions


def test_get_active_transactions_date_filter(db_session: Session, sample_transactions):  # type: ignore[no-untyped-def]
    """Test getting transactions with date filter."""
    transactions = get_active_transactions(
        db_session,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        exclude_duplicates=True,
    )

    assert len(transactions) == 3  # 4 January transactions - 1 duplicate


def test_get_active_transactions_category_filter(  # type: ignore[no-untyped-def]
    db_session: Session, sample_transactions
):
    """Test getting transactions with category filter."""
    transactions = get_active_transactions(
        db_session, category="食費", exclude_duplicates=True
    )

    assert len(transactions) == 2  # 1 in Jan + 1 in Feb (excluding duplicate)
    assert all(t.category_major == "食費" for t in transactions)


def test_get_monthly_summary_exclude_duplicates(  # type: ignore[no-untyped-def]
    db_session: Session, sample_transactions
):
    """Test monthly summary excluding duplicates."""
    summary = get_monthly_summary(db_session, 2024, 1, exclude_duplicates=True)

    assert summary["total_income"] == 200000.0
    assert summary["total_expense"] == -8000.0  # -5000 + -3000
    assert summary["net"] == 192000.0
    assert summary["transaction_count"] == 3
    assert summary["duplicate_count"] == 1


def test_get_monthly_summary_include_duplicates(  # type: ignore[no-untyped-def]
    db_session: Session, sample_transactions
):
    """Test monthly summary including duplicates."""
    summary = get_monthly_summary(db_session, 2024, 1, exclude_duplicates=False)

    assert summary["total_income"] == 200000.0
    assert summary["total_expense"] == -13000.0  # -5000 + -5000 + -3000
    assert summary["net"] == 187000.0
    assert summary["transaction_count"] == 4


def test_get_category_breakdown(db_session: Session, sample_transactions):  # type: ignore[no-untyped-def]
    """Test category breakdown."""
    breakdown = get_category_breakdown(
        db_session,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        exclude_duplicates=True,
    )

    # Should have 3 categories: 食費, 交通費, 収入
    assert len(breakdown) == 3

    # Find 食費 category
    food = next(c for c in breakdown if c["category"] == "食費")
    assert food["total_amount"] == -5000.0  # Only one transaction, duplicate excluded
    assert food["transaction_count"] == 1


def test_get_category_breakdown_with_duplicates(  # type: ignore[no-untyped-def]
    db_session: Session, sample_transactions
):
    """Test category breakdown including duplicates."""
    breakdown = get_category_breakdown(
        db_session,
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        exclude_duplicates=False,
    )

    # Find 食費 category
    food = next(c for c in breakdown if c["category"] == "食費")
    assert food["total_amount"] == -10000.0  # Both transactions included
    assert food["transaction_count"] == 2


def test_get_duplicate_impact_report(db_session: Session, sample_transactions):  # type: ignore[no-untyped-def]
    """Test duplicate impact report."""
    report = get_duplicate_impact_report(db_session, 2024, 1)

    assert "with_duplicates" in report
    assert "without_duplicates" in report
    assert "impact" in report

    # Check impact
    impact = report["impact"]
    assert impact["expense_difference"] == -5000.0  # Duplicate amount
    assert impact["income_difference"] == 0.0  # No income duplicates
    assert impact["duplicate_transaction_count"] == 1


def test_get_active_transactions_empty_result(db_session: Session):  # type: ignore[no-untyped-def]
    """Test getting transactions with no results."""
    transactions = get_active_transactions(
        db_session,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 31),
    )

    assert len(transactions) == 0


def test_get_monthly_summary_no_transactions(db_session: Session):  # type: ignore[no-untyped-def]
    """Test monthly summary with no transactions."""
    summary = get_monthly_summary(db_session, 2025, 1)

    assert summary["total_income"] == 0
    assert summary["total_expense"] == 0
    assert summary["net"] == 0
    assert summary["transaction_count"] == 0
    assert summary["duplicate_count"] == 0
