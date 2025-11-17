# asyncio moved to local import in other tests
from collections.abc import Sequence

import pytest
from mcp.types import Tool

from household_mcp.server import list_tools


@pytest.mark.anyio
async def test_list_tools_smoke():
    tools: Sequence[Tool] = await list_tools()
    names = {t.name for t in tools}
    assert {
        "monthly_summary",
        "category_analysis",
        "find_categories",
    }.issubset(names)
