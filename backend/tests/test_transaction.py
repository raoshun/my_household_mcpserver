def test_transaction_model():
    from datetime import date

    from household_mcp.models.transaction import Transaction

    tran = Transaction(
        id=1, date=date(2024, 10, 1), amount=-5000, category_id=1, account_id=1
    )
    assert tran.amount == -5000
