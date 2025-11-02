from __future__ import annotations

import time
from pathlib import Path

from household_mcp.dataloader import HouseholdDataLoader


def _write_month(dir_: Path, year: int, month: int, amount: int = -1000) -> Path:
    # Simplified CSV generator
    # Ensure filename aligns with loader expectation
    from calendar import monthrange

    end_day = monthrange(year, month)[1]
    name = f"収入・支出詳細_{year}-{month:02d}-01_{year}-{month:02d}-{end_day:02d}.csv"
    path = dir_ / name
    content = (
        "日付,計算対象,金額（円）,大項目,中項目\n"
        f"{year}-{month:02d}-01,1,{amount},食費,自炊\n"
    )
    path.write_text(content, encoding="cp932")
    return path


def test_cache_stats_hit_miss(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    _write_month(data_dir, 2025, 7, -1200)

    loader = HouseholdDataLoader(src_dir=data_dir)
    assert loader.cache_stats() == {"hits": 0, "misses": 0, "size": 0}

    # First load -> miss
    loader.load_month(2025, 7)
    stats_after_first = loader.cache_stats()
    assert stats_after_first["misses"] == 1
    assert stats_after_first["hits"] == 0
    assert stats_after_first["size"] == 1

    # Second load (no change) -> hit
    loader.load_month(2025, 7)
    stats_after_second = loader.cache_stats()
    assert stats_after_second["hits"] == 1
    assert stats_after_second["misses"] == 1

    # Modify file mtime -> miss again
    csv_path = next(data_dir.glob("収入・支出詳細_2025-07-01_2025-07-31.csv"))
    time.sleep(1.1)  # ensure mtime change
    csv_path.write_text(
        csv_path.read_text(encoding="cp932").replace("-1200", "-1500"),
        encoding="cp932",
    )
    loader.load_month(2025, 7)
    stats_after_modify = loader.cache_stats()
    assert stats_after_modify["misses"] == 2
    assert stats_after_modify["hits"] == 1

    # Clear cache resets stats
    loader.clear_cache()
    assert loader.cache_stats() == {"hits": 0, "misses": 0, "size": 0}
