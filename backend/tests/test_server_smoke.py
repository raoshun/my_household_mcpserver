import asyncio
from collections.abc import Sequence

from mcp.types import Tool

from household_mcp.server import list_tools


def test_list_tools_smoke():
    tools: Sequence[Tool] = asyncio.run(list_tools())
    names = {t.name for t in tools}
    assert {"monthly_summary", "category_analysis", "find_categories"}.issubset(names)
