"""Category model for household MCP server."""

from pydantic import BaseModel


class Category(BaseModel):
    """
    Represents a transaction category.

    Attributes:
        id: Unique identifier for the category.
        name: Display name of the category.
        parent_id: Optional parent category ID for hierarchical categories.

    """

    id: int
    name: str
    parent_id: int | None = None
