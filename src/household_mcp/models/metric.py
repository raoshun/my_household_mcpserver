"""Metric model for household MCP server."""

from pydantic import BaseModel


class Metric(BaseModel):
    """Represents a calculated metric or KPI.

    Attributes:
        name: Name of the metric.
        description: Human-readable description of what the metric measures.
        formula: Formula or calculation method for the metric.
    """

    name: str
    description: str
    formula: str
