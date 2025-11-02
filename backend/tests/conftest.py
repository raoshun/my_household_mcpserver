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

    # Debug: Print dependency availability
    import os
    data_dir = os.environ.get("HOUSEHOLD_DATA_DIR", "tests/fixtures/data")
    if not data_dir.startswith("/"):
        data_path = root / data_dir
    else:
        data_path = Path(data_dir)
    print(f"\n📁 Data directory: {data_path}")
    print(f"   Exists: {data_path.exists()}")
    if data_path.exists():
        csv_files = list(data_path.glob("*.csv"))
        print(f"   CSV files: {len(csv_files)}")

    # Suppress matplotlib glyph warnings (already filtered in code)
    warnings.filterwarnings(
        "ignore",
        message=r"Glyph .* missing from current font",
        category=UserWarning,
    )
    # Suppress dateutil utcfromtimestamp deprecation warning in output
    warnings.filterwarnings(
        "ignore",
        message=r"datetime\.datetime\.utcfromtimestamp\(\) is deprecated",
        category=DeprecationWarning,
    )


# Configure anyio to use only asyncio backend (trio not installed)
@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


# ========================= Optional Extras Auto-Skip =========================
# Detect optional dependencies availability
try:  # DB extras (sqlalchemy)
    import sqlalchemy

    HAS_DB = True
except Exception:
    HAS_DB = False

try:  # Web/streaming extras (fastapi)
    import fastapi

    HAS_WEB = True
except Exception:
    HAS_WEB = False


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    root = Path(str(config.rootpath))
    for item in list(items):
        path = Path(str(item.fspath))
        try:
            rel = path.relative_to(root)
            rel_str = str(rel)
        except Exception:
            # If path is outside root, fall back to absolute string
            rel_str = str(path)
        filename = path.name

        # DB-related tests: unit/database, unit/duplicate, duplicate tools/workflow
        is_db_test = (
            "tests/unit/database/" in rel_str
            or "tests/unit/duplicate/" in rel_str
            or filename.startswith("test_duplicate")
            or "duplicate_workflow" in rel_str
            or filename == "test_duplicate_tools.py"
        )
        if is_db_test and not HAS_DB:
            item.add_marker(pytest.mark.skip(reason="requires db extras (sqlalchemy)"))
            continue

        # Web/Streaming-related tests: trend API, streaming pipeline
        is_web_test = filename in {"test_trend_integration.py"} or rel_str.endswith(
            "integration/test_streaming_pipeline.py"
        )
        if is_web_test and not HAS_WEB:
            item.add_marker(
                pytest.mark.skip(reason="requires web/streaming extras (fastapi)")
            )
            continue


@pytest.fixture(scope="session")
def extras_available() -> dict[str, bool]:
    return {"db": HAS_DB, "web": HAS_WEB}


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    """Ignore collecting tests that require unavailable optional extras.

    Uses pathlib.Path per pytest 9 deprecations. This prevents ImportError
    at collection time for modules that import optional dependencies at the
    top level (e.g., SQLAlchemy, FastAPI).
    """
    p = collection_path
    s = str(p)
    fname = p.name

    is_db_test = (
        "/tests/unit/database/" in s
        or "/tests/unit/duplicate/" in s
        or fname.startswith("test_duplicate")
        or "duplicate_workflow" in s
        or fname == "test_duplicate_tools.py"
    )
    if is_db_test and not HAS_DB:
        return True

    is_web_test = fname == "test_trend_integration.py" or s.endswith(
        "/integration/test_streaming_pipeline.py"
    )
    if is_web_test and not HAS_WEB:
        return True

    return False


@pytest.fixture(autouse=True)
def _reset_streaming_global_cache_between_tests() -> None:
    """Reset streaming global cache before each test to avoid order coupling.

    Some tests assert the initial state of GLOBAL_CHART_CACHE. Since other tests
    may initialize it via ensure_global_cache(), we clear it to preserve
    test independence.
    """
    try:
        import household_mcp.streaming.global_cache as gc

        gc.GLOBAL_CHART_CACHE = None
    except Exception:
        # Streaming extras not installed; nothing to reset
        pass
