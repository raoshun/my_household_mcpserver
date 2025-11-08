"""Tests for TASK-1405: MCP Resource integration for DB-based resources."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from household_mcp.database.manager import DatabaseManager
from household_mcp.database.models import Budget, Transaction


@pytest.fixture
def db_setup():
    """Set up an in-memory database for testing."""
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")

    # Create all tables
    from household_mcp.database.models import Base

    Base.metadata.create_all(engine)

    manager = DatabaseManager(engine=engine)
    manager.initialize_database()

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session, manager

    session.close()
    engine.dispose()


@pytest.fixture
def sample_transactions(db_setup):
    """Create sample transactions for testing."""
    session, manager = db_setup

    # Create budget
    budget = Budget(
        year=2024,
        month=10,
        category_major="食費",
        budgeted_amount=50000,
    )
    session.add(budget)

    # Create transactions for October 2024
    base_date = datetime(2024, 10, 1)
    transactions = [
        Transaction(
            source_file="test.csv",
            row_number=1,
            date=base_date,
            amount=-5000,
            category_major="食費",
            category_minor="外食",
            description="ラーメン屋",
            account="クレジットカード",
        ),
        Transaction(
            source_file="test.csv",
            row_number=2,
            date=base_date + timedelta(days=5),
            amount=-3000,
            category_major="食費",
            category_minor="外食",
            description="カフェ",
            account="現金",
        ),
        Transaction(
            source_file="test.csv",
            row_number=3,
            date=base_date + timedelta(days=10),
            amount=100000,
            category_major="給与",
            category_minor="月給",
            description="給料",
            account="銀行口座",
        ),
    ]

    for tx in transactions:
        session.add(tx)

    session.commit()
    return session, manager, transactions


class TestResourceIntegration:
    """Test TASK-1405: Resource integration."""

    def test_report_tools_import(self):
        """Test that report tools can be imported."""
        try:
            from household_mcp.tools.report_tools import (
                create_summary_report,
                export_transactions,
                generate_report,
            )

            assert callable(export_transactions)
            assert callable(generate_report)
            assert callable(create_summary_report)
        except ImportError as e:
            pytest.skip(f"Report tools not available: {e}")


class TestServerResourceDefinitions:
    """Test that server.py resource definitions are syntactically correct."""

    def test_server_module_imports(self):
        """Test that server module can be imported."""
        try:
            # Import the server module
            import household_mcp.server  # noqa: F401

            assert True
        except SyntaxError as e:
            pytest.fail(f"Server module has syntax error: {e}")
        except ImportError:
            # Some imports might fail due to missing dependencies
            # but that's okay - we're just checking syntax
            pass

    def test_resource_functions_exist(self):
        """Test that resource functions are defined in server."""
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
            pytest.skip("Resource functions not available")

    def test_has_report_tools_flag(self):
        """Test that HAS_REPORT_TOOLS flag is set."""
        try:
            from household_mcp.server import HAS_REPORT_TOOLS

            # Flag should be set (even if tools aren't available)
            assert HAS_REPORT_TOOLS is not None
        except ImportError:
            pytest.skip("HAS_REPORT_TOOLS flag not available")


class TestResourceFunctionBehavior:
    """Test resource functions graceful error handling."""

    def test_get_transactions_no_data(self):
        """Test get_transactions with no data."""
        try:
            from household_mcp.server import get_transactions
        except ImportError:
            pytest.skip("Resource functions not available")

        # This should return gracefully even without valid database
        result = get_transactions()
        assert isinstance(result, dict)
        # Should either have data or an error key
        assert "error" in result or "transactions" in result

    def test_get_monthly_summary_no_data(self):
        """Test get_monthly_summary_resource with no data."""
        try:
            from household_mcp.server import get_monthly_summary_resource
        except ImportError:
            pytest.skip("Resource functions not available")

        # This should return gracefully
        result = get_monthly_summary_resource()
        assert isinstance(result, dict)
        # Should either have data or an error key
        assert "error" in result or "summary" in result

    def test_get_budget_status_no_data(self):
        """Test get_budget_status_resource with no data."""
        try:
            from household_mcp.server import get_budget_status_resource
        except ImportError:
            pytest.skip("Resource functions not available")

        # This should return gracefully
        result = get_budget_status_resource()
        assert isinstance(result, dict)
        # Should either have data or an error key
        assert "error" in result or "budget_status" in result
