"""Pytest configuration for the household MCP server tests."""

import sys
import warnings
from pathlib import Path

import pytest


def pytest_configure():
    # Ensure 'src' is importable for tests
    root = Path(__file__).resolve().parent.parent
    src_path = root / "src"
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

    # Suppress matplotlib glyph warnings globally (already filtered in code, double-safety)
    warnings.filterwarnings(
        "ignore",
        message=r"Glyph .* missing from current font",
        category=UserWarning,
    )
    # Suppress dateutil utcfromtimestamp deprecation warning in test output
    warnings.filterwarnings(
        "ignore",
        message=r"datetime\.datetime\.utcfromtimestamp\(\) is deprecated",
        category=DeprecationWarning,
    )


# Configure anyio to use only asyncio backend (trio not installed)
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
