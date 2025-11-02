"""Duplicate detection package for household MCP server."""

from .detector import DetectionOptions, DuplicateDetector
from .service import DuplicateService

__all__ = [
    "DetectionOptions",
    "DuplicateDetector",
    "DuplicateService",
]
