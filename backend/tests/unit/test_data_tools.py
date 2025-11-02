import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from household_mcp.database.connection import DatabaseConnection
from household_mcp.exceptions import ValidationError
from household_mcp.tools.data_tools import (
    AccountManager,
    CategoryManager,
    TransactionManager,
)


class TempDB(DatabaseConnection):
    def __init__(self, db_dir: Path):
        super().__init__(str(db_dir / "test.db"))


@pytest.fixture()
def temp_db(tmp_path: Path):
    db = TempDB(tmp_path)
    # Ensure connection and schema created
    conn = db.connect()
    try:
        # Create schema for testing
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                type TEXT NOT NULL,
                balance REAL DEFAULT 0.0,
                initial_balance REAL DEFAULT 0.0,
                current_balance REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parent_id INTEGER,
                color TEXT,
                icon TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(name, type)
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                category_id INTEGER,
                account_id INTEGER,
                type TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (account_id) REFERENCES accounts(id)
            );
        """
        )
        conn.commit()
    except Exception as e:
        print(f"Failed to create schema: {e}")
        raise
    yield db
    db.close()


@pytest.fixture()
def managers(temp_db: TempDB):
    # Inject the temp DatabaseConnection
    acc = AccountManager(db_connection=temp_db)
    cat = CategoryManager()
    # Monkeypatch CategoryManager to use our temp DB
    cat.db_connection = temp_db
    tm = TransactionManager()
    tm.db_connection = temp_db
    return acc, cat, tm


def test_account_crud(managers):
    acc, _cat, _tm = managers

    # Explicitly create required account for test isolation
    res = acc.add_account("財布", "cash", initial_balance=1000.0, is_active=True)
    assert res["success"] is True
    account_id = res["account_id"]

    # Read
    account = acc.get_account(account_id)
    assert account and account["name"] == "財布"

    # Update
    upd = acc.update_account(
        account_id, name="財布-改", account_type="cash", is_active=False
    )
    assert upd["success"] is True

    # Update balance
    bal = acc.update_balance(account_id, 1200.0)
    assert bal["success"] is True
    assert bal["new_balance"] == 1200.0

    # List
    accounts = acc.get_accounts()
    assert any(a["id"] == account_id for a in accounts)

    # Delete
    de = acc.delete_account(account_id)
    assert de["success"] is True


def test_category_crud(managers):
    acc, cat, tm = managers

    # Explicitly create required category for test isolation
    res = cat.add_category("外食", "expense")
    assert res["success"] is True
    category_id = res["category_id"]

    # Get categories
    lst = cat.get_categories("expense")
    assert lst["success"] is True and lst["count"] >= 1

    # Update category
    up = cat.update_category(category_id, name="外食-改", type="expense")
    assert up["success"] is True

    # Prevent delete when in use
    acc.add_account("口座", "bank", initial_balance=0)
    _ = acc.get_accounts()[0]["id"]
    # Create a transaction that uses the category
    add_txn = tm.add_transaction(
        "2024-01-01", 500, "lunch", "外食-改", "口座", "expense"
    )
    assert add_txn["success"] is True
    cannot_delete = cat.delete_category(category_id)
    assert (
        cannot_delete["success"] is False
        and cannot_delete["error"] == "CATEGORY_IN_USE"
    )

    # Delete after removing dependency
    # We'll delete the transaction and then try again
    txns = tm.get_transactions(limit=1)["data"]["transactions"]
    del_res = tm.delete_transaction(txns[0]["id"]) if txns else {"success": False}
    assert del_res["success"] is True
    can_delete = cat.delete_category(category_id)
    assert can_delete["success"] is True


def test_transaction_flows(managers):
    acc, cat, tm = managers

    # Explicitly create required accounts and categories for test isolation
    acc.add_account("現金", "cash", initial_balance=5000.0, is_active=True)
    cat.add_category("食費", "expense")
    cat.add_category("給料", "income")

    # Add income
    add_income = tm.add_transaction(
        "2024-01-10", 10000, "給与", "給料", "現金", "income"
    )
    assert add_income["success"] is True

    # Add expense
    add_expense = tm.add_transaction(
        "2024-01-11", 2000, "昼食", "食費", "現金", "expense"
    )
    assert add_expense["success"] is True

    # List and filter
    all_txns = tm.get_transactions(limit=10)
    assert (
        all_txns["success"] is True
        and all_txns["data"]["pagination"]["total_count"] >= 2
    )

    # Update
    txns = all_txns["data"]["transactions"]
    target = txns[0]
    upd = tm.update_transaction(target["id"], description="修正")
    assert upd["success"] is True

    # Delete
    dele = tm.delete_transaction(target["id"])
    assert dele["success"] is True


@pytest.mark.parametrize(
    "bad",
    [
        (None, 100, "desc", "cat", "acc", "expense"),
        ("2024-01-01", -1, "desc", "cat", "acc", "expense"),
        ("2024-01-01", 100, "", "cat", "acc", "expense"),
        ("2024-01-01", 100, "desc", "", "acc", "expense"),
        ("2024-01-01", 100, "desc", "cat", "", "expense"),
        ("2024-01-01", 100, "desc", "cat", "acc", "other"),
    ],
)
def test_add_transaction_validation_errors(managers, bad):
    _, _, tm = managers
    date, amount, desc, cat, acc, typ = bad
    res = tm.add_transaction(date, amount, desc, cat, acc, typ)
    assert res["success"] is False


# Error Handling Tests for Phase 3
def test_account_manager_database_errors(temp_db):
    """Test database error handling in AccountManager."""
    acc = AccountManager(db_connection=temp_db)

    # Test database connection error simulation with add_account (returns dict)
    with patch.object(temp_db, "transaction") as mock_transaction:
        mock_transaction.side_effect = sqlite3.Error("Database connection failed")

        result = acc.add_account("TestAccount", "cash", initial_balance=1000.0)
        assert result["success"] is False
        assert "Database connection failed" in result["error"]


def test_transaction_manager_nonexistent_account(managers):
    """Test TransactionManager with non-existent account reference."""
    _, _, tm = managers

    # Try to add transaction with non-existent account
    result = tm.add_transaction(
        date="2024-01-01",
        amount=1000,
        description="Test",
        category_name="食費",
        account_name="NonExistentAccount",
        transaction_type="expense",
    )
    assert result["success"] is False
    assert "アカウント 'NonExistentAccount' が見つかりません" in result["error"]


def test_transaction_manager_invalid_date_format(managers):
    """Test TransactionManager with invalid date format."""
    acc, _, tm = managers

    # Create account first
    acc.add_account("TestAccount", "cash", initial_balance=1000.0)

    # Test invalid date format - should trigger exception in datetime parsing
    with patch("household_mcp.tools.data_tools.datetime") as mock_datetime:
        mock_datetime.strptime.side_effect = ValueError("Invalid date format")

        result = tm.add_transaction(
            date="invalid-date",
            amount=100,
            description="Test",
            category_name="食費",
            account_name="TestAccount",
            transaction_type="expense",
        )
        assert result["success"] is False
        assert "日付はYYYY-MM-DD形式で入力してください" in result["error"]


def test_transaction_manager_get_transactions_database_error(managers):
    """Test get_transactions with database error."""
    _, _, tm = managers

    with patch.object(tm.db_connection, "execute_query") as mock_execute:
        mock_execute.side_effect = sqlite3.Error("Query execution failed")

        result = tm.get_transactions()
        assert result["success"] is False
        assert "取引の取得に失敗しました" in result["message"]


def test_category_manager_constraint_violation(temp_db):
    """Test CategoryManager database constraint violations."""
    cat = CategoryManager()
    cat.db_connection = temp_db

    # Create category first
    cat.add_category("TestCategory", "expense")

    # Try to create duplicate - should trigger constraint error
    with patch.object(temp_db, "transaction") as mock_transaction:
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.execute.side_effect = sqlite3.IntegrityError(
            "UNIQUE constraint failed"
        )
        mock_conn.cursor.return_value = mock_cursor
        mock_transaction.return_value.__enter__.return_value = mock_conn

        result = cat.add_category("TestCategory", "expense")
        assert result["success"] is False


def test_account_manager_update_nonexistent_account(managers):
    """Test updating non-existent account."""
    acc, _, _ = managers

    result = acc.update_account(999999, name="UpdatedName")
    assert result["success"] is False
    assert "NOT_FOUND" in result["error"]


def test_transaction_manager_delete_nonexistent(managers):
    """Test deleting non-existent transaction."""
    _, _, tm = managers

    result = tm.delete_transaction(999999)
    assert result["success"] is False
    assert "Transaction not found" in result["error"]


def test_transaction_update_with_invalid_category(managers):
    """Test transaction update with invalid category reference."""
    acc, _, tm = managers

    # Setup: create account and transaction
    acc.add_account("TestAccount", "cash", initial_balance=1000.0)
    result = tm.add_transaction(
        date="2024-01-01",
        amount=100,
        description="Test",
        category_name="食費",
        account_name="TestAccount",
        transaction_type="expense",
    )
    transaction_id = result["transaction_id"]

    # Test update with account that doesn't exist
    result = tm.update_transaction(
        transaction_id=transaction_id, account_name="NonExistentAccount"
    )
    assert result["success"] is False
    assert "アカウント 'NonExistentAccount' が見つかりません" in result["error"]


def test_category_creation_database_error(temp_db):
    """Test category creation with database error during insert."""
    tm = TransactionManager()
    tm.db_connection = temp_db

    # Mock category creation failure
    with patch.object(tm, "_get_category_id") as mock_get_cat:
        mock_get_cat.side_effect = ValidationError("カテゴリーの作成に失敗しました")

        # Setup account first
        acc = AccountManager(db_connection=temp_db)
        acc.add_account("TestAccount", "cash", initial_balance=1000.0)

        result = tm.add_transaction(
            date="2024-01-01",
            amount=100,
            description="Test",
            category_name="NewCategory",
            account_name="TestAccount",
            transaction_type="expense",
        )
        assert result["success"] is False
