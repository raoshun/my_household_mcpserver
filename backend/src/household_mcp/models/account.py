"""Account model for household MCP server."""

from pydantic import BaseModel


class Account(BaseModel):
    """Represents a financial account.

    Attributes:
        id: Unique identifier for the account.
        name: Display name of the account.
        type: Type of account (e.g., checking, savings, credit).
    """

    id: int
    name: str
    type: str
