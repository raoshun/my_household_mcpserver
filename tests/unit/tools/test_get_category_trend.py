from __future__ import annotations

import csv
from pathlib import Path

import pytest

from household_mcp.tools.trend_tool import category_trend_summary, get_category_trend


def _write_csv(dir_path: Path, year: int, month: int, rows: list[list[str]]) -> None:
    # ファイル名は DataLoader が期待する形式
    from calendar import monthrange

    end_day = monthrange(year, month)[1]
    fname = f"収入・支出詳細_{year}-{month:02d}-01_{year}-{month:02d}-{end_day:02d}.csv"
    file_path = dir_path / fname
    # cp932 で書き込む（DataLoader は cp932 で読む）
    with open(file_path, "w", encoding="cp932", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["日付", "計算対象", "金額（円）", "大項目", "中項目"]
        )  # 必須列
        writer.writerows(rows)


@pytest.fixture()
def sample_data_dir(tmp_path: Path) -> Path:
    # 2025-06, 2025-07 に食費の支出を作成
    _write_csv(
        tmp_path,
        2025,
        6,
        rows=[
            ["2025-06-10", 1, -6000, "食費", "食料品"],
            ["2025-06-20", 1, -1000, "交通", "電車"],
        ],
    )
    _write_csv(
        tmp_path,
        2025,
        7,
        rows=[
            ["2025-07-05", 1, -5000, "食費", "食料品"],
            ["2025-07-12", 1, -2000, "交通", "バス"],
        ],
    )
    return tmp_path


def test_get_category_trend_with_category(sample_data_dir: Path) -> None:
    resp = get_category_trend(
        category="食費",
        start_month="2025-06",
        end_month="2025-07",
        src_dir=str(sample_data_dir),
    )

    assert resp["category"] == "食費"
    assert resp["start_month"] == "2025-06"
    assert resp["end_month"] == "2025-07"
    assert isinstance(resp["metrics"], list) and len(resp["metrics"]) == 2
    assert "食費の 2025年06月〜2025年07月" in resp["text"]


def test_get_category_trend_without_category_returns_top(sample_data_dir: Path) -> None:
    resp = get_category_trend(
        category=None,
        start_month="2025-06",
        end_month="2025-07",
        src_dir=str(sample_data_dir),
        top_n=1,
    )

    assert resp["category"] is None
    assert resp["top_categories"]
    assert resp["top_categories"][0] in {"食費", "交通"}
    assert resp["details"] and resp["details"][0]["metrics"]


def test_category_trend_summary(sample_data_dir: Path) -> None:
    resp = category_trend_summary(src_dir=str(sample_data_dir), window=12, top_n=1)

    assert "months" in resp and len(resp["months"]) == 2
    assert "top_categories" in resp and len(resp["top_categories"]) == 1
    top = resp["top_categories"][0]
    assert top in resp["metrics"]
    assert isinstance(resp["metrics"][top], list) and resp["metrics"][top]
