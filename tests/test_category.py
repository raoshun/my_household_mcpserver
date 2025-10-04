def test_category_model():
    from household_mcp.models.category import Category

    cat = Category(id=1, name="食費")
    assert cat.name == "食費"
