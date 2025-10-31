"""Tests for logging configuration."""

import logging

import pytest

from household_mcp.logging_config import HAS_STRUCTLOG, get_logger, setup_logging


def test_setup_logging_standard():
    """Test standard logging setup."""
    setup_logging(level="DEBUG", use_structlog=False)

    logger = logging.getLogger("test")
    assert logger.level <= logging.DEBUG


def test_setup_logging_info_level():
    """Test logging level configuration."""
    # Reset root logger first
    logging.root.handlers = []
    setup_logging(level="INFO")

    # Root logger should be at INFO level
    assert logging.root.level == logging.INFO


def test_get_logger_standard():
    """Test get_logger returns correct logger type."""
    setup_logging(use_structlog=False)

    logger = get_logger("test_standard")

    # Should return standard logging logger when structlog not used
    if not HAS_STRUCTLOG:
        assert isinstance(logger, logging.Logger)


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_setup_logging_structlog():
    """Test structlog setup (only if installed)."""
    setup_logging(level="DEBUG", use_structlog=True, json_format=False)

    logger = get_logger("test_structlog")
    # Should not raise error
    logger.info("test message", extra_field="value")


@pytest.mark.skipif(not HAS_STRUCTLOG, reason="structlog not installed")
def test_setup_logging_structlog_json():
    """Test structlog with JSON format."""
    setup_logging(level="INFO", use_structlog=True, json_format=True)

    logger = get_logger("test_json")
    # Should not raise error
    logger.info("json test", key="value", count=42)


def test_setup_logging_structlog_fallback():
    """Test fallback to standard logging when structlog not available."""
    # Force use_structlog=True even without structlog (should fallback)
    if not HAS_STRUCTLOG:
        setup_logging(level="WARNING", use_structlog=True)

        # Should fall back to standard logging
        logger = logging.getLogger("test_fallback")
        assert isinstance(logger, logging.Logger)
