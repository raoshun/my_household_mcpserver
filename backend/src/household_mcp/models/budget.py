"""Budget model for household MCP server."""

from pydantic import BaseModel


class Budget(BaseModel):
    """
    Represents a budget allocation for a category.

    Attributes:
        category_id: ID of the category this budget applies to.
        amount: Budget amount in the smallest currency unit.
        period: Budget period (e.g., monthly, yearly).

    """

    category_id: int
    amount: int
    period: str
