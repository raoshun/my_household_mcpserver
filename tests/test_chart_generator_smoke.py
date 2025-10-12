import io

import pandas as pd
import pytest

# household_mcp.visualization.chart_generatorの依存関係（matplotlib等）が未インストールの場合はテストをスキップします
try:
    from household_mcp.visualization.chart_generator import (
        HAS_VISUALIZATION_DEPS,
        ChartGenerator,
    )
except Exception:  # pragma: no cover - import guard
    ChartGenerator = None  # type: ignore
    HAS_VISUALIZATION_DEPS = False  # type: ignore

pytestmark = pytest.mark.skipif(
    not HAS_VISUALIZATION_DEPS, reason="visualization deps not installed"
)


def sample_pie_df():
    return pd.DataFrame(
        {
            "category": ["食費", "交通", "光熱費"],
            "amount": [25000, 8000, 12000],
        }
    )


def sample_trend_df():
    return pd.DataFrame(
        {
            "month": ["2025-06", "2025-07", "2025-08", "2025-09"],
            "amount": [30000, 28000, 32000, 31000],
        }
    )


def sample_bar_df():
    return pd.DataFrame(
        {
            "カテゴリ": ["食費", "交通", "光熱費", "日用品"],
            "金額": [25000, 8000, 12000, 6000],
        }
    )


def _assert_png(buffer: io.BytesIO):
    assert isinstance(buffer, io.BytesIO)
    data = buffer.getvalue()
    assert len(data) > 8
    # PNG signature check
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("size", ["800x600", "1000x500", "300x300"])
def test_pie_chart_smoke(size):
    gen = ChartGenerator()
    buf = gen.create_monthly_pie_chart(
        sample_pie_df(), title="テスト: 月次支出構成", image_size=size
    )
    _assert_png(buf)


@pytest.mark.parametrize("size", ["800x600", "640x480"])
def test_trend_line_smoke(size):
    gen = ChartGenerator()
    buf = gen.create_category_trend_line(
        sample_trend_df(), category="食費", image_size=size
    )
    _assert_png(buf)


@pytest.mark.parametrize("size", ["800x600", "1024x512"])
def test_bar_chart_smoke(size):
    gen = ChartGenerator()
    buf = gen.create_comparison_bar_chart(
        sample_bar_df(), title="カテゴリ比較", image_size=size
    )
    _assert_png(buf)
