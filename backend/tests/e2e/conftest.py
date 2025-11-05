"""
Pytest configuration and fixtures for E2E tests.

Provides Playwright browser instances and page fixtures
for cross-browser E2E testing.
"""

from __future__ import annotations

from typing import Any, Generator

import pytest


def _get_browser() -> Generator[Any, None, None]:
    """Lazy import and provide browser for tests."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            # Use Chromium browser
            browser_instance = playwright.chromium.launch(headless=True)
            yield browser_instance
            browser_instance.close()
    except ImportError:
        pytest.skip("Playwright not installed. Install with: " "pip install playwright")


@pytest.fixture(scope="session")
def browser() -> Generator[Any, None, None]:
    """Provide a Playwright browser instance for the test session."""
    yield from _get_browser()


@pytest.fixture(autouse=True)
def browser_cleanup() -> Generator[None, None, None]:
    """Cleanup fixture to ensure all contexts are closed."""
    yield
    # Cleanup happens automatically with context managers
