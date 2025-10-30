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


# ========== TASK-606: 拡張テスト ==========


def test_chart_generator_all_graph_types():
    """全グラフタイプが正常に生成できることを確認"""
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")

    gen = ChartGenerator(font_path=font_path)

    # 円グラフ
    pie_buf = gen.create_monthly_pie_chart(sample_pie_data(), title="円グラフテスト")
    assert isinstance(pie_buf, io.BytesIO)
    assert pie_buf.getbuffer().nbytes > 1000  # 最低限のサイズ確認

    # 折れ線グラフ
    line_buf = gen.create_category_trend_line(
        sample_line_data(), category="食費", title="折れ線グラフテスト"
    )
    assert isinstance(line_buf, io.BytesIO)
    assert line_buf.getbuffer().nbytes > 1000

    # 棒グラフ
    bar_buf = gen.create_comparison_bar_chart(
        sample_bar_data(), title="棒グラフテスト"
    )
    assert isinstance(bar_buf, io.BytesIO)
    assert bar_buf.getbuffer().nbytes > 1000


def test_chart_generator_japanese_font_rendering():
    """日本語フォントが正しくロードされ、日本語テキストがレンダリングできることを確認"""
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")

    gen = ChartGenerator(font_path=font_path)

    # 日本語を含むデータ
    japanese_data = pd.DataFrame(
        {
            "category": ["食費・飲料", "住居費", "光熱・水道"],
            "amount": [50000, 80000, 15000],
        }
    )

    buf = gen.create_monthly_pie_chart(
        japanese_data, title="日本語タイトル：家計簿分析"
    )
    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 1000


def test_chart_generator_empty_data_error():
    """空データでエラーが発生することを確認"""
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")

    gen = ChartGenerator(font_path=font_path)

    empty_df = pd.DataFrame({"category": [], "amount": []})

    with pytest.raises(ChartGenerationError, match="データが空"):
        gen.create_monthly_pie_chart(empty_df)


def test_chart_generator_missing_columns_error():
    """必須列が欠けている場合にエラーが発生することを確認"""
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")

    gen = ChartGenerator(font_path=font_path)

    # 'amount' 列がない
    invalid_df = pd.DataFrame({"category": ["食費", "住居費"], "value": [10000, 20000]})

    with pytest.raises(ChartGenerationError):
        gen.create_monthly_pie_chart(invalid_df)


def test_chart_generator_invalid_font_path():
    """無効なフォントパスでもフォールバックで動作することを確認"""
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    # 存在しないフォントパスを指定
    gen = ChartGenerator(font_path="/nonexistent/font.ttf")

    # フォールバックで動作するはず（matplotlib のデフォルトフォント使用）
    buf = gen.create_monthly_pie_chart(sample_pie_data(), title="Test")
    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 1000


def test_chart_generator_large_dataset_performance():
    """大量データでも適切な時間内に処理できることを確認（NFR-005）"""
    if not HAS_VISUALIZATION_DEPS:
        pytest.skip("Visualization依存関係が見つからないためテストをスキップします")

    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        pytest.skip("日本語フォントが見つからないためテストをスキップします")

    gen = ChartGenerator(font_path=font_path)

    # 100カテゴリの大量データ
    large_data = pd.DataFrame(
        {
            "category": [f"カテゴリ{i}" for i in range(100)],
            "amount": [i * 1000 for i in range(100)],
        }
    )

    import time

    start = time.time()
    buf = gen.create_monthly_pie_chart(large_data, title="大量データテスト")
    elapsed = time.time() - start

    assert isinstance(buf, io.BytesIO)
    assert buf.getbuffer().nbytes > 1000
    assert elapsed < 3.0, f"生成時間が3秒を超えました: {elapsed:.2f}秒"
