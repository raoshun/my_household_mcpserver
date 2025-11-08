"""
Logging configuration module for household MCP server.

This module provides utilities to configure logging, including
structured logging with structlog when the 'logging' extra is installed.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

# Check if structlog is available
try:
    import structlog  # type: ignore

    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False


def setup_logging(
    level: str = "INFO",
    use_structlog: bool = False,
    json_format: bool = False,
) -> None:
    """
    Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_structlog: Use structlog for structured logging (requires 'logging' extra)
        json_format: Output logs in JSON format (requires structlog)

    Example:
        >>> # Basic logging
        >>> setup_logging(level="INFO")

        >>> # Structured logging with JSON output
        >>> setup_logging(level="DEBUG", use_structlog=True, json_format=True)

    """
    log_level = getattr(logging, level.upper(), logging.INFO)

    if use_structlog and not HAS_STRUCTLOG:
        logging.warning(
            "structlog not installed. Install with: pip install household-mcp-server[logging]"
        )
        use_structlog = False

    if use_structlog:
        _setup_structlog(log_level, json_format)
    else:
        _setup_standard_logging(log_level)


def _setup_standard_logging(level: int) -> None:
    """Configure standard Python logging."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stderr,
    )


def _setup_structlog(level: int, json_format: bool) -> None:
    """Configure structlog for structured logging."""
    if not HAS_STRUCTLOG:
        return

    # Configure stdlib logging
    logging.basicConfig(
        format="%(message)s",
        level=level,
        stream=sys.stderr,
    )

    # Build processor chain
    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,  # type: ignore
        structlog.stdlib.add_log_level,  # type: ignore
        structlog.stdlib.add_logger_name,  # type: ignore
        structlog.processors.TimeStamper(fmt="iso"),  # type: ignore
        structlog.processors.StackInfoRenderer(),  # type: ignore
    ]

    if json_format:
        processors.append(  # type: ignore
            structlog.processors.JSONRenderer()  # type: ignore
        )
    else:
        processors.extend(
            [
                structlog.dev.ConsoleRenderer(  # type: ignore
                    colors=sys.stderr.isatty(),
                    exception_formatter=(structlog.dev.plain_traceback),  # type: ignore
                )
            ]
        )

    # Configure structlog
    structlog.configure(  # type: ignore
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,  # type: ignore
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),  # type: ignore
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> Any:
    """
    Get a logger instance.

    Args:
        name: Logger name (default: calling module name)

    Returns:
        Logger instance (structlog or standard logging)

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started", version="0.1.0")

    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)  # type: ignore
    else:
        return logging.getLogger(name)
