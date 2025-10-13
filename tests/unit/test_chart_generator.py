import io
from pathlib import Path

import pandas as pd
import pytest

from household_mcp.exceptions import ChartGenerationError
from household_mcp.visualization.chart_generator import (
    HAS_VISUALIZATION_DEPS,
    ChartGenerator,
)


def sample_pie_data():
    return pd.DataFrame(
        {"category": ["食費", "住居費", "光熱費"], "amount": [30000, 50000, 15000]}
    )


def sample_line_data():
    return pd.DataFrame(
        {"month": ["2025-01", "2025-02", "2025-03"], "amount": [25000, 27000, 26000]}
    )


def sample_bar_data():
    return pd.DataFrame(
        {"category": ["医療費", "教育費", "娯楽費"], "amount": [8000, 12000, 5000]}
    )


def test_create_monthly_pie_chart():
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")
    gen = ChartGenerator(font_path=font_path)
    buf = gen.create_monthly_pie_chart(sample_pie_data(), title="テスト円グラフ")
    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 0


def test_create_category_trend_line():
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")
    gen = ChartGenerator(font_path=font_path)
    buf = gen.create_category_trend_line(
        sample_line_data(), category="食費", title="推移テスト"
    )
    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 0


def test_create_comparison_bar_chart():
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")
    gen = ChartGenerator(font_path=font_path)
    buf = gen.create_comparison_bar_chart(sample_bar_data(), title="比較棒グラフ")
    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 0


def test_invalid_data_raises():
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")

    gen = ChartGenerator(font_path=font_path)
    with pytest.raises(ChartGenerationError):
        gen.create_monthly_pie_chart(pd.DataFrame({"foo": [1], "bar": [2]}))
