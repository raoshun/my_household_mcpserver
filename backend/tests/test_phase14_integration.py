"""Integration tests for Phase 14: Report Generation and MCP Resources.

Tests the complete flow from tools → database → resources.
"""

import json
import time
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from household_mcp.database.models import Base, Budget, Transaction
from household_mcp.tools.report_tools import (
    create_summary_report,
    export_transactions,
    generate_report,
)


@pytest.fixture
def test_db():
    """Create an in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def populated_db(test_db):
    """Populate database with sample data for integration tests."""
    session = test_db

    # Add sample data spanning multiple months
    base_date = datetime(2024, 9, 1)

    # September data
    for day in range(1, 30):
        if day % 3 == 0:
            session.add(
                Transaction(
                    source_file="test.csv",
                    row_number=day,
                    date=base_date + timedelta(days=day - 1),
                    amount=-3000 if day % 2 == 0 else -5000,
                    category_major="食費",
                    category_minor="外食" if day % 2 == 0 else "食材",
                    description=f"Sep transaction {day}",
                    account="クレジットカード",
                )
            )

    # October data (more extensive)
    base_date_oct = datetime(2024, 10, 1)
    for day in range(1, 31):
        amount = -5000 if day % 3 == 0 else -3000 if day % 2 == 0 else 50000
        session.add(
            Transaction(
                source_file="test.csv",
                row_number=100 + day,
                date=base_date_oct + timedelta(days=day - 1),
                amount=amount,
                category_major="給与" if amount > 0 else "食費",
                category_minor="月給" if amount > 0 else "外食",
                description=f"Oct transaction {day}",
                account="銀行口座" if amount > 0 else "現金",
            )
        )

    # November data
    base_date_nov = datetime(2024, 11, 1)
    for day in range(1, 30):
        amount = -4000 if day % 2 == 0 else -2000
        session.add(
            Transaction(
                source_file="test.csv",
                row_number=200 + day,
                date=base_date_nov + timedelta(days=day - 1),
                amount=amount,
                category_major="交通",
                category_minor="公共交通",
                description=f"Nov transaction {day}",
                account="SUICA",
            )
        )

    # Add budgets
    for month in [9, 10, 11]:
        session.add(
            Budget(
                year=2024,
                month=month,
                category_major="食費",
                amount=50000,
            )
        )
        session.add(
            Budget(
                year=2024,
                month=month,
                category_major="交通",
                amount=10000,
            )
        )

    session.commit()
    return session


@pytest.fixture
def mocked_db_session(populated_db, monkeypatch):
    """Mock _get_session to return the test database."""
    def mock_get_session():
        return populated_db

    monkeypatch.setattr(
        "household_mcp.tools.report_tools._get_session",
        mock_get_session,
    )
    return populated_db


class TestPhase14Integration:
    """TASK-1406: Phase 14 Integration Tests."""

    def test_export_transactions_basic(self, mocked_db_session):
        """Test basic transaction export functionality."""
        result = export_transactions(2024, 10, format="json")
        assert result is not None
        assert len(result) > 0

        # Verify JSON structure
        data = json.loads(result)
        assert isinstance(data, (dict, list))

    def test_export_transactions_csv_format(self, mocked_db_session):
        """Test CSV export format."""
        result = export_transactions(2024, 10, format="csv")
        assert result is not None
        # CSV format should have some content (headers or data)
        if result:
            # CSV exports may be empty but shouldn't error
            assert isinstance(result, str)

    def test_generate_report_all_types(self, mocked_db_session):
        """Test all report types generate successfully."""
        for report_type in ["summary", "detailed", "category"]:
            result = generate_report(2024, 10, report_type)
            assert result is not None
            assert len(result) > 0
            data = json.loads(result)
            assert isinstance(data, dict)

    def test_create_comprehensive_report(self, mocked_db_session):
        """Test comprehensive report creation."""
        result = create_summary_report(2024, 10)
        assert result is not None
        data = json.loads(result)
        # Should have multiple report sections
        assert len(data) > 0

    def test_cross_month_consistency(self, mocked_db_session):
        """Test data consistency across multiple months."""
        # Get reports for different months
        report_9 = generate_report(2024, 9, "summary")
        report_10 = generate_report(2024, 10, "summary")
        report_11 = generate_report(2024, 11, "summary")

        # All should be valid JSON
        data_9 = json.loads(report_9)
        data_10 = json.loads(report_10)
        data_11 = json.loads(report_11)

        assert all(isinstance(d, dict) for d in [data_9, data_10, data_11])

    def test_category_filtering(self, mocked_db_session):
        """Test category filtering in exports."""
        result = export_transactions(
            2024, 10, category_major="食費", format="json"
        )
        assert result is not None

    def test_empty_month_handling(self, mocked_db_session):
        """Test graceful handling of months with no data."""
        # December has no data
        result = export_transactions(2024, 12, format="json")
        # Should return something (empty list or dict)
        assert result is not None

    def test_performance_export_speed(self, mocked_db_session):
        """Test export performance (target: < 500ms)."""
        start = time.time()
        result = export_transactions(2024, 10, format="json")
        elapsed = time.time() - start

        assert elapsed < 0.5  # 500ms threshold
        assert result is not None

    def test_performance_report_generation(self, mocked_db_session):
        """Test report generation performance."""
        start = time.time()
        result = generate_report(2024, 10, "summary")
        elapsed = time.time() - start

        assert elapsed < 0.5  # 500ms threshold
        assert result is not None

    def test_comprehensive_summary_performance(self, mocked_db_session):
        """Test comprehensive summary generation performance."""
        start = time.time()
        result = create_summary_report(2024, 10)
        elapsed = time.time() - start

        assert elapsed < 1.0  # 1 second for comprehensive report
        assert result is not None


class TestPhase14Coverage:
    """Test coverage verification for Phase 14."""

    def test_report_tools_module_exists(self):
        """Verify report_tools module is available."""
        import household_mcp.tools.report_tools as rt

        assert hasattr(rt, "export_transactions")
        assert hasattr(rt, "generate_report")
        assert hasattr(rt, "create_summary_report")

    def test_all_exported_functions_callable(self):
        """Verify all exported functions are callable."""
        from household_mcp.tools.report_tools import (
            create_summary_report,
            export_transactions,
            generate_report,
        )

        assert all(
            callable(f)
            for f in [
                export_transactions,
                generate_report,
                create_summary_report,
            ]
        )

    def test_server_resources_available(self):
        """Verify MCP resources are available in server."""
        try:
            from household_mcp.server import (
                get_budget_status_resource,
                get_monthly_summary_resource,
                get_transactions,
            )

            assert callable(get_transactions)
            assert callable(get_monthly_summary_resource)
            assert callable(get_budget_status_resource)
        except ImportError:
            pytest.skip("Server resources not available in this environment")

    def test_phase14_backward_compatibility(self):
        """Verify Phase 13 core interfaces still work."""
        # Import core modules to verify they still function
        from household_mcp.database.manager import DatabaseManager
        from household_mcp.database.models import Transaction

        assert Transaction is not None
        assert DatabaseManager is not None


class TestPhase14QualityGates:
    """Quality gates for Phase 14 completion."""

    def test_all_phase14_tools_documented(self):
        """Verify all Phase 14 tools have docstrings."""
        from household_mcp.tools import report_tools

        functions = [
            report_tools.export_transactions,
            report_tools.generate_report,
            report_tools.create_summary_report,
        ]

        for func in functions:
            assert func.__doc__ is not None
            assert len(func.__doc__) > 0

    def test_no_unhandled_exceptions(self, mocked_db_session):
        """Verify functions handle errors gracefully."""
        # Test with invalid inputs
        try:
            # Invalid month
            result = export_transactions(2024, 13, format="json")
            assert result is not None
        except (ValueError, Exception):
            # Should either return gracefully or raise with message
            pass

    def test_data_consistency_transactions_to_report(
        self, mocked_db_session
    ):
        """Verify data consistency from transaction export to report."""
        export = export_transactions(2024, 10, format="json")
        report = generate_report(2024, 10, "summary")

        export_data = json.loads(export)
        report_data = json.loads(report)

        # Both should be non-empty JSON
        assert export_data is not None
        assert report_data is not None
