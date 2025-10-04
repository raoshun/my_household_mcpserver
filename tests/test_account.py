def test_account_model():
    from household_mcp.models.account import Account

    acc = Account(id=1, name="三井住友", type="bank")
    assert acc.type == "bank"
