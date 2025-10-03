def test_transaction_model():
    from src.household_mcp.models.transaction import Transaction
    from datetime import date
    tran = Transaction(id=1, date=date(2024,10,1), amount=-5000, category_id=1, account_id=1)
    assert tran.amount == -5000
