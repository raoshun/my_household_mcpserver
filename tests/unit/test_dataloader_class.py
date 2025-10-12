"""Tests for the HouseholdDataLoader class (class-specific behaviors)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from household_mcp.dataloader import DataSourceError, HouseholdDataLoader


def test_category_hierarchy_latest() -> None:
    loader = HouseholdDataLoader(src_dir="data")
    # 確実に一つ以上の月がある前提（既存テストと同じ前提）
    hierarchy = loader.category_hierarchy()
    assert hierarchy, "カテゴリ階層が空ではいけない"
    # value は list[str]
    any_middle = next(iter(hierarchy.values()))
    assert isinstance(any_middle, list)


def test_cache_behaviour(tmp_path: Path) -> None:
    # 簡易 CSV を 1 ファイル生成
    content = (
        "日付,計算対象,金額（円）,大項目,中項目\n"
        "2025-07-01,1,-1000,食費,外食\n"
        "2025-07-02,1,-2000,食費,自炊\n"
    )
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # ファイル名仕様に合わせる
    csv_path = data_dir / "収入・支出詳細_2025-07-01_2025-07-31.csv"
    csv_path.write_text(content, encoding="cp932")

    loader = HouseholdDataLoader(src_dir=data_dir)
    df1 = loader.load_month(2025, 7)
    assert loader.cache_size() == 1
    # 未変更ならキャッシュヒット (オブジェクトは copy なので同一 identity ではない)
    df2 = loader.load_month(2025, 7)
    assert loader.cache_size() == 1
    assert df1.equals(df2)

    # ファイル更新 (mtime 変更)
    time.sleep(1.1)  # mtime 解像度用に待機
    csv_path.write_text(content.replace("-1000", "-1500"), encoding="cp932")
    df3 = loader.load_month(2025, 7)
    assert loader.cache_size() == 1  # 置き換え
    assert df3["金額（円）"].min() == -2000  # -1500 と -2000 のはず
    # 変更を検出: 旧DFの合計金額と異なるはず（単純比較）
    assert df1["金額（円）"].sum() != df3["金額（円）"].sum()


def test_load_missing(tmp_path: Path) -> None:
    with pytest.raises(DataSourceError):
        HouseholdDataLoader(src_dir=tmp_path / "not-exist")
