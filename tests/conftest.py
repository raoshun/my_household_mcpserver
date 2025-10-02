"""Pytest configuration for the household MCP server tests."""

from __future__ import annotations

import sys
from pathlib import Path


def pytest_configure() -> None:
    root = Path(__file__).resolve().parent.parent
    src_path = root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
