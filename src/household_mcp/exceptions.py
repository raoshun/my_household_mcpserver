"""Custom exception hierarchy for the household MCP server."""

from __future__ import annotations


class HouseholdMCPError(Exception):
    """Base exception for domain-specific errors inside the MCP server."""


class ValidationError(HouseholdMCPError):
    """Raised when user input or query parameters are invalid."""


class DataSourceError(HouseholdMCPError):
    """Raised when the underlying CSV data source cannot be accessed or parsed."""


class AnalysisError(HouseholdMCPError):
    """Raised when analytical computations cannot be completed (e.g., lack of data)."""
