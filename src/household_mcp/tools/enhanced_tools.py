"""Enhanced MCP tools for image-capable responses.

Provides wrappers that can return either text or image outputs.
Connects ChartGenerator → Global ChartCache → HTTP endpoint URL.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict

import pandas as pd

from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.exceptions import DataSourceError

# Visualization is optional
try:  # pragma: no cover - optional deps
    from household_mcp.visualization.chart_generator import ChartGenerator

    HAS_VIZ = True
except Exception:  # pragma: no cover
    HAS_VIZ = False

try:  # pragma: no cover - optional deps
    from household_mcp.streaming.global_cache import ensure_global_cache

    HAS_STREAMING = True
except Exception:  # pragma: no cover
    HAS_STREAMING = False


@dataclass(frozen=True)
class HttpConfig:
    host: str = os.getenv("HOUSEHOLD_HTTP_HOST", "localhost")
    port: int = int(os.getenv("HOUSEHOLD_HTTP_PORT", "8000"))


def _data_dir() -> str:
    return os.getenv("HOUSEHOLD_DATA_DIR", "data")


def _parse_image_size(size_str: str) -> str:
    # Basic validation e.g., "800x600"
    return size_str if "x" in size_str else "800x600"


def _build_cache_key_params(**kwargs: Any) -> Dict[str, Any]:
    # Keep stable ordering by relying on ChartCache.sort_keys=True
    return kwargs


def enhanced_monthly_summary(
    year: int,
    month: int,
    *,
    output_format: str = "text",
    graph_type: str = "pie",
    image_size: str = "800x600",
    image_format: str = "png",
) -> Dict[str, Any]:
    """Enhanced monthly summary that can return an image URL.

    Returns dict with either text data or image metadata.
    """
    if output_format not in {"text", "image"}:
        return {"success": False, "error": "Invalid output_format"}

    # Load monthly data
    try:
        df = HouseholdDataLoader(_data_dir()).load_month(year, month)
    except DataSourceError as e:
        return {"success": False, "error": str(e)}

    if output_format == "text":
        # Simple textual aggregation by category
        summary = (
            df.groupby("大項目", observed=False)["金額（円）"].sum().abs().sort_values(ascending=False)
        )
        total = int(summary.sum())
        top5 = [{"category": str(k), "amount": int(v)} for k, v in summary.head(5).items()]
        return {
            "success": True,
            "type": "text",
            "year": year,
            "month": month,
            "total_expense": total,
            "top5": top5,
        }

    # Image path requires optional deps
    if not HAS_VIZ:
        return {
            "success": False,
            "error": "Visualization dependencies not installed. Install: household-mcp-server[visualization]",
        }
    if not HAS_STREAMING:
        return {
            "success": False,
            "error": "Streaming dependencies not installed. Install: household-mcp-server[streaming]",
        }

    # Prepare chart data for pie chart: category & positive amount
    chart_df = pd.DataFrame(
        {
            "category": df["大項目"].astype(str),
            "amount": df["金額（円）"].abs(),
        }
    )

    # Generate chart
    gen = ChartGenerator()
    size = _parse_image_size(image_size)
    if graph_type == "pie":
        buffer = gen.create_monthly_pie_chart(chart_df, title=f"{year}年{month}月 支出構成", image_size=size)
    else:
        # Fallback to pie if unsupported graph_type for monthly summary
        buffer = gen.create_monthly_pie_chart(chart_df, title=f"{year}年{month}月 支出構成", image_size=size)

    image_bytes = buffer.getvalue()

    # Cache and build URL
    cache = ensure_global_cache()
    if cache is None:
        return {
            "success": False,
            "error": "Chart cache unavailable. Install: household-mcp-server[streaming]",
        }

    params = _build_cache_key_params(
        kind="monthly",
        year=year,
        month=month,
        graph_type=graph_type,
        image_size=size,
        image_format=image_format,
    )
    key = cache.get_key(params)
    cache.set(key, image_bytes)

    conf = HttpConfig()
    url = f"http://{conf.host}:{conf.port}/api/charts/{key}"

    return {
        "success": True,
        "type": "image",
        "url": url,
        "cache_key": key,
        "media_type": "image/png",
        "alt_text": f"{year}年{month}月の支出構成（{graph_type}）",
    }
