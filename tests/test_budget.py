def test_budget_model():
    from household_mcp.models.budget import Budget

    bud = Budget(category_id=1, amount=30000, period="2024-10")
    assert bud.amount == 30000
