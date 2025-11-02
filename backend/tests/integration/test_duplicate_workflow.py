"""Integration tests for duplicate detection with real data.

NOTE: These tests require the 'db' extra to be installed.
They are skipped automatically in environments without SQLAlchemy.
"""

# flake8: noqa: F811

import os
from datetime import date
from pathlib import Path

import pytest

# Check if database dependencies are available
try:
    from household_mcp.database import (
        DatabaseManager,
        get_active_transactions,
        get_duplicate_impact_report,
        get_monthly_summary,
    )
    from household_mcp.database.csv_importer import CSVImporter
    from household_mcp.database.models import DuplicateCheck, Transaction
    from household_mcp.duplicate import DetectionOptions, DuplicateService

    HAS_DB = True
except ImportError:
    HAS_DB = False
    DatabaseManager = None
    CSVImporter = None
    Transaction = None
    DuplicateCheck = None
    DetectionOptions = None
    DuplicateService = None
    get_active_transactions = None
    get_duplicate_impact_report = None
    get_monthly_summary = None

pytestmark = pytest.mark.skipif(not HAS_DB, reason="requires db extras (sqlalchemy)")


@pytest.fixture(scope="module")
def test_db_path(tmp_path_factory):  # type: ignore[no-untyped-def]
    """Create a shared temporary database path for this module."""
    tmpdir = tmp_path_factory.mktemp("dupdb")
    db_path = tmpdir / "test_household.db"
    return str(db_path)


@pytest.fixture(scope="module")
def db_manager(test_db_path):  # type: ignore[no-untyped-def]
    """Create a shared database manager with test database for this module."""
    manager = DatabaseManager(test_db_path)
    manager.initialize_database()  # Create tables
    yield manager
    # Cleanup once per module
    try:
        manager.close()
    finally:
        if os.path.exists(test_db_path):
            os.remove(test_db_path)


@pytest.fixture
def csv_data_dir():  # type: ignore[no-untyped-def]
    """Get the path to CSV data directory."""
    # Try multiple possible paths
    possible_paths = [
        Path(__file__).parent.parent.parent / "data",  # From tests/integration
        Path.cwd() / "data",  # From project root
        Path(__file__).resolve().parent.parent.parent / "data",  # Absolute path
    ]

    for data_dir in possible_paths:
        if data_dir.exists() and data_dir.is_dir():
            csv_files = list(data_dir.glob("*.csv"))
            if csv_files:
                return str(data_dir)

    pytest.skip(f"Data directory not found. Tried: {[str(p) for p in possible_paths]}")


@pytest.fixture
def imported_data(db_manager, csv_data_dir):  # type: ignore[no-untyped-def]
    """Import real CSV data into test database (idempotent).

    既に取り込み済みの場合は再インポートをスキップし、レコード件数を返す。
    """
    with db_manager.session_scope() as session:
        # すでに取り込み済みであれば、再取り込みをスキップ
        existing = session.query(Transaction).count()
        if existing > 0:
            return existing
        importer = CSVImporter(session)
        result = importer.import_all_csvs(csv_data_dir)
        return result["total_imported"]


def test_full_workflow_with_real_data(db_manager, imported_data):  # type: ignore[no-untyped-def]
    """Test complete duplicate detection workflow with real data.

    This test:
    1. Imports real CSV data
    2. Runs duplicate detection
    3. Confirms some duplicates
    4. Verifies aggregation excludes duplicates
    """
    # Step 1: Verify data import
    with db_manager.session_scope() as session:
        total_transactions = session.query(Transaction).count()
        assert total_transactions == imported_data
        assert total_transactions > 0  # Should have real data

    # Step 2: Run duplicate detection with reasonable tolerances
    with db_manager.session_scope() as session:
        service = DuplicateService(session)
        options = DetectionOptions(
            date_tolerance_days=0,  # Same day only
            amount_tolerance_abs=0.0,  # Exact amount
            amount_tolerance_pct=0.0,
            min_similarity_score=0.95,  # High confidence
        )
        detected_count = service.detect_and_save_candidates(options)

        # Should find some duplicate candidates (if any exist)
        print(f"Detected {detected_count} duplicate candidates")

        # Get candidates
        candidates = service.get_pending_candidates(limit=10)
        print(f"Pending candidates: {len(candidates)}")

        if detected_count > 0:
            # Step 3: Confirm first candidate as duplicate (if exists)
            check = session.query(DuplicateCheck).first()
            if check:
                result = service.confirm_duplicate(check.id, "duplicate")
                assert result["success"] is True
                assert "marked_transaction_id" in result

                # Verify transaction is marked
                marked_id = result["marked_transaction_id"]
                marked_trans = (
                    session.query(Transaction)
                    .filter(Transaction.id == marked_id)
                    .first()
                )
                assert marked_trans.is_duplicate == 1
                assert marked_trans.duplicate_of is not None

    # Step 4: Verify aggregation excludes duplicates
    with db_manager.session_scope() as session:
        # Get active transactions (excluding duplicates)
        active = get_active_transactions(session, exclude_duplicates=True)
        all_trans = get_active_transactions(session, exclude_duplicates=False)

        # Active should be less than or equal to all
        assert len(active) <= len(all_trans)

        # Count duplicates
        duplicate_count = (
            session.query(Transaction).filter(Transaction.is_duplicate == 1).count()
        )
        expected_active = len(all_trans) - duplicate_count
        assert len(active) == expected_active


def test_monthly_summary_excludes_duplicates(db_manager, imported_data):  # type: ignore[no-untyped-def]
    """Test that monthly summary correctly excludes duplicates."""
    if imported_data == 0:
        pytest.skip("No data imported")

    # Create a duplicate for testing
    with db_manager.session_scope() as session:
        # Find a transaction to duplicate
        original = session.query(Transaction).first()
        if not original:
            pytest.skip("No transactions found")

        # Create duplicate
        duplicate = Transaction(
            source_file=original.source_file,
            row_number=original.row_number + 10000,
            date=original.date,
            amount=original.amount,
            description=original.description,
            category_major=original.category_major,
            category_minor=original.category_minor,
            account=original.account,
            is_duplicate=1,
            duplicate_of=original.id,
        )
        session.add(duplicate)
        session.commit()

        # Get year and month from transaction
        year = original.date.year
        month = original.date.month

    # Get summaries with and without duplicates
    with db_manager.session_scope() as session:
        summary_without = get_monthly_summary(
            session, year, month, exclude_duplicates=True
        )
        summary_with = get_monthly_summary(
            session, year, month, exclude_duplicates=False
        )

        # With duplicates should have higher count
        assert summary_with["transaction_count"] > summary_without["transaction_count"]
        assert summary_with["duplicate_count"] >= 1

        # Amounts should differ by the duplicate amount
        if original.amount < 0:
            assert summary_with["total_expense"] < summary_without["total_expense"]
        else:
            assert summary_with["total_income"] > summary_without["total_income"]


def test_duplicate_detection_performance(db_manager, imported_data):  # type: ignore[no-untyped-def]
    """Test that duplicate detection completes in reasonable time."""
    if imported_data == 0:
        pytest.skip("No data imported")

    import time

    with db_manager.session_scope() as session:
        service = DuplicateService(session)
        options = DetectionOptions(
            date_tolerance_days=1,
            amount_tolerance_abs=100.0,
            min_similarity_score=0.8,
        )

        start_time = time.time()
        detected_count = service.detect_and_save_candidates(options)
        elapsed_time = time.time() - start_time

        print(f"Detection completed in {elapsed_time:.2f} seconds")
        print(f"Detected {detected_count} candidates")

        # Should complete in reasonable time (less than 30 seconds for ~11k records)
        assert elapsed_time < 30.0


def test_restore_duplicate_workflow(db_manager, imported_data):  # type: ignore[no-untyped-def]
    """Test that restoring duplicates works correctly."""
    if imported_data == 0:
        pytest.skip("No data imported")

    with db_manager.session_scope() as session:
        # Create a test duplicate
        original = session.query(Transaction).first()
        if not original:
            pytest.skip("No transactions found")

        duplicate = Transaction(
            source_file=original.source_file,
            row_number=original.row_number + 20000,
            date=original.date,
            amount=original.amount,
            description=original.description,
            category_major=original.category_major,
            is_duplicate=1,
            duplicate_of=original.id,
        )
        session.add(duplicate)
        session.commit()
        duplicate_id = int(duplicate.id)  # Convert to int for type safety

    # Restore the duplicate
    with db_manager.session_scope() as session:
        service = DuplicateService(session)
        result = service.restore_duplicate(duplicate_id)
        assert result["success"] is True

    # Verify restoration
    with db_manager.session_scope() as session:
        restored = (
            session.query(Transaction).filter(Transaction.id == duplicate_id).first()
        )
        assert restored.is_duplicate == 0
        assert restored.duplicate_of is None


def test_get_stats_with_real_data(db_manager, imported_data):  # type: ignore[no-untyped-def]
    """Test getting statistics with real data."""
    if imported_data == 0:
        pytest.skip("No data imported")

    with db_manager.session_scope() as session:
        service = DuplicateService(session)

        # baseline stats before detection (module-scoped DB may already have checks)
        baseline = service.get_stats()

        # Run detection
        options = DetectionOptions(min_similarity_score=0.95)
        detected_count = service.detect_and_save_candidates(options)

        # Get stats
        stats = service.get_stats()

        assert stats["total_transactions"] == imported_data
        assert stats["total_checks"] == baseline["total_checks"] + detected_count
        assert stats["pending_checks"] >= detected_count  # none confirmed in this test
        assert stats["duplicate_transactions"] >= 0  # none confirmed yet in this test


def test_duplicate_impact_report(db_manager, imported_data):  # type: ignore[no-untyped-def]
    """Test duplicate impact report with real data."""
    if imported_data == 0:
        pytest.skip("No data imported")

    with db_manager.session_scope() as session:
        # Create a test duplicate in January 2024
        trans = (
            session.query(Transaction)
            .filter(Transaction.date >= date(2024, 1, 1))
            .filter(Transaction.date < date(2024, 2, 1))
            .first()
        )

        if not trans:
            pytest.skip("No January 2024 transactions found")

        duplicate = Transaction(
            source_file=trans.source_file,
            row_number=trans.row_number + 30000,
            date=trans.date,
            amount=trans.amount,
            description=trans.description,
            category_major=trans.category_major,
            is_duplicate=1,
            duplicate_of=trans.id,
        )
        session.add(duplicate)
        session.commit()

    # Get impact report
    with db_manager.session_scope() as session:
        report = get_duplicate_impact_report(session, 2024, 1)

        assert "with_duplicates" in report
        assert "without_duplicates" in report
        assert "impact" in report

        # Should show difference
        impact = report["impact"]
        assert impact["duplicate_transaction_count"] >= 1

        # Amount difference should be non-zero
        total_diff = impact["expense_difference"] + impact["income_difference"]
        assert total_diff != 0


def test_category_filtering_with_duplicates(db_manager, imported_data):  # type: ignore[no-untyped-def]
    """Test that category filtering works with duplicate exclusion."""
    if imported_data == 0:
        pytest.skip("No data imported")

    with db_manager.session_scope() as session:
        # Get first transaction and its category
        trans = session.query(Transaction).first()
        if not trans or not trans.category_major:
            pytest.skip("No categorized transactions found")

        category = trans.category_major

        # Create a duplicate in the same category
        duplicate = Transaction(
            source_file=trans.source_file,
            row_number=trans.row_number + 40000,
            date=trans.date,
            amount=trans.amount,
            description=trans.description,
            category_major=category,
            is_duplicate=1,
            duplicate_of=trans.id,
        )
        session.add(duplicate)
        session.commit()

    # Get transactions with category filter
    with db_manager.session_scope() as session:
        with_dup = get_active_transactions(
            session, category=category, exclude_duplicates=False
        )
        without_dup = get_active_transactions(
            session, category=category, exclude_duplicates=True
        )

        assert len(with_dup) > len(without_dup)
        assert all(t.category_major == category for t in without_dup)
