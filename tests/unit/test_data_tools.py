from pathlib import Path

import pytest

from household_mcp.database.connection import DatabaseConnection
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
        conn.execute("SELECT 1")
    finally:
        # ここでは接続確認のみを行い、特別な後処理は不要です
        pass
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
    acc, cat, tm = managers

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
