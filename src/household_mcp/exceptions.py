"""Custom exception hierarchy for the household MCP server."""

from __future__ import annotations


class HouseholdMCPError(Exception):
    """Base exception for domain-specific errors inside the MCP server."""


class ValidationError(HouseholdMCPError):
    """Raised when user input or query parameters are invalid.

    Extended to optionally carry a ``field`` attribute so legacy validation
    helpers (e.g. utils.validators) can attach the field name that failed.
    This unifies previously duplicated ValidationError definitions into this
    single canonical implementation.
    """

    def __init__(self, message: str = "Validation error", field: str | None = None):
        self.field = field
        # Maintain a ``message`` attribute for backward compatibility with
        # code that accessed ``e.message`` (not standard in modern Python).
        self.message = message
        super().__init__(message)


class DataSourceError(HouseholdMCPError):
    """Raised when the underlying CSV data source cannot be accessed or parsed."""


class AnalysisError(HouseholdMCPError):
    """Raised when analytical computations cannot be completed (e.g., lack of data)."""
