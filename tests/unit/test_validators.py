from datetime import date, datetime
from decimal import Decimal

import pytest

from household_mcp.exceptions import ValidationError
from household_mcp.utils.validators import DataValidator, validate_bulk_data


class TestDataValidator:
    def test_validate_date_iso(self):
        assert DataValidator.validate_date("2024-01-31") == date(2024, 1, 31)

    def test_validate_date_various_formats(self):
        # supported formats: YYYY/MM/DD, MM/DD/YYYY, MM-DD-YYYY
        assert DataValidator.validate_date("2024/02/29") == date(2024, 2, 29)
        assert DataValidator.validate_date("12/31/2023") == date(2023, 12, 31)
        assert DataValidator.validate_date("12-31-2023") == date(2023, 12, 31)
        # datetime/date passthrough
        dt = datetime(2023, 8, 15, 10, 0, 0)
        assert DataValidator.validate_date(dt) == date(2023, 8, 15)
        assert DataValidator.validate_date(date(2023, 7, 1)) == date(2023, 7, 1)

    def test_validate_date_invalid(self):
        with pytest.raises(ValidationError):
            DataValidator.validate_date("2024-13-01")
        with pytest.raises(ValidationError):
            DataValidator.validate_date(12345)
        with pytest.raises(ValidationError):
            DataValidator.validate_date("")

    def test_validate_amount_basic(self):
        assert DataValidator.validate_amount(100) == Decimal("100")
        assert DataValidator.validate_amount("1,234") == Decimal("1234")
        assert DataValidator.validate_amount("¥5,678") == Decimal("5678")
        assert DataValidator.validate_amount("１２３４") == Decimal("1234")

    def test_validate_amount_invalid(self):
        with pytest.raises(ValidationError):
            DataValidator.validate_amount(None)
        with pytest.raises(ValidationError):
            DataValidator.validate_amount("abc")
        # 無効な全角文字（例：「１２３ａ」）のテストケース
        with pytest.raises(ValidationError):
            DataValidator.validate_amount("１２３ａ")

    def test_validate_string_rules(self):
        assert DataValidator.validate_string(" food ", "field", True, 1, 10) == "food"
        assert DataValidator.validate_string(None, "field", required=False) is None
        with pytest.raises(ValidationError):
            DataValidator.validate_string("", "field")
        with pytest.raises(ValidationError):
            DataValidator.validate_string("x", "field", True, 2)
        with pytest.raises(ValidationError):
            DataValidator.validate_string("x" * 11, "field", True, 0, 10)
        with pytest.raises(ValidationError):
            DataValidator.validate_string(
                "AA-11", "field", True, 0, 50, r"^[A-Z]{2}[0-9]{3}$"
            )

    def test_validate_enum(self):
        assert (
            DataValidator.validate_enum("Income", "type", ["income", "expense"])
            == "income"
        )
        with pytest.raises(ValidationError):
            DataValidator.validate_enum("other", "type", ["income", "expense"])

    def test_validate_transaction_data(self):
        ok = DataValidator.validate_transaction_data(
            {
                "date": "2024-01-01",
                "amount": 1000,
                "description": "lunch",
                "type": "expense",
            }
        )
        assert ok["date"] == date(2024, 1, 1)
        assert ok["amount"] == Decimal("1000")
        assert ok["description"] == "lunch"
        assert ok["type"] == "expense"

    def test_validate_category_data(self):
        ok = DataValidator.validate_category_data(
            {"name": "食費", "type": "expense", "color": "#FF00AA"}
        )
        assert ok["name"] == "食費"
        assert ok["type"] == "expense"
        assert ok["color"] == "#FF00AA"

    def test_validate_account_data(self):
        ok = DataValidator.validate_account_data(
            {"name": "現金", "type": "cash", "initial_balance": 0}
        )
        assert ok["name"] == "現金"
        assert ok["type"] == "cash"
        assert ok["initial_balance"] == Decimal("0")


class TestValidateBulkData:
    def test_bulk_success_and_errors(self):
        data = [
            {
                "date": "2024-01-01",
                "amount": 1000,
                "description": "ok",
                "type": "income",
            },
            {"date": "bad", "amount": "x", "description": "", "type": "expense"},
        ]
        result = validate_bulk_data(data, "transaction")
        assert result["valid_count"] == 1
        assert result["error_count"] == 1
        assert len(result["errors"]) == 1
        assert result["validated_data"][0]["amount"] == Decimal("1000")

    def test_bulk_invalid_type(self):
        with pytest.raises(ValueError):
            validate_bulk_data([], "unknown")
