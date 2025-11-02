"""Transaction model for household MCP server."""

from datetime import date

from pydantic import BaseModel


class Transaction(BaseModel):
    """
    Represents a financial transaction.

    Attributes:
        id: Unique identifier for the transaction.
        date: Date when the transaction occurred.
        amount: Transaction amount in the smallest currency unit.
        category_id: ID of the category this transaction belongs to.
        account_id: ID of the account this transaction is associated with.
        memo: Optional memo or description for the transaction.

    """

    id: int
    date: date
    amount: int
    category_id: int
    account_id: int
    memo: str = ""
