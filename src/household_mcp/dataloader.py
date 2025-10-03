from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Iterable, Optional, Sequence, Tuple

import pandas as pd

from .exceptions import DataSourceError

ENCODING = "cp932"
CATEGORY_COLUMNS = ("大項目", "中項目")
COLUMN_ALIASES = {
    "大分類": "大項目",
    "中分類": "中項目",
}
REQUIRED_COLUMNS = {"計算対象", "金額（円）", "日付"}

MonthTuple = Tuple[int, int]


@dataclass(frozen=True)
class LoaderConfig:
    """設定値をまとめたデータクラス。必要になれば拡張しやすい形にしておく。"""

    src_dir: Path


class HouseholdDataLoader:
    """家計簿 CSV データを読み込み・加工するためのクラス。"""

    def __init__(self, src_dir: str | Path = "data") -> None:
        self._config = LoaderConfig(src_dir=self._resolve_src_dir(src_dir))
        self._month_cache: dict[MonthTuple, tuple[pd.DataFrame, float]] = {}

    def month_csv_path(self, year: int, month: int) -> Path:
        return self._config.src_dir / self._make_filename(year, month)

    @property
    def src_dir(self) -> Path:
        """Public accessor for source directory (read-only)."""
        return self._config.src_dir

    def load(self, year: Optional[int] = None, month: Optional[int] = None) -> pd.DataFrame:
        base_dir = self._config.src_dir
        if year is None:
            files = sorted(base_dir.glob("*.csv"))
        elif month is None:
            files = sorted(base_dir.glob(f"収入・支出詳細_{year}-*_*.csv"))
        else:
            files = [self.month_csv_path(year, month)]
        if not files:
            raise DataSourceError("指定条件に該当するCSVファイルが存在しません")
        frames = [self._read_csv(p) for p in files]
        df = pd.concat(frames, ignore_index=True)
        return self._post_process(df)

    def load_month(self, year: int, month: int) -> pd.DataFrame:
        key = (year, month)
        path = self.month_csv_path(year, month)
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError as exc:  # pragma: no cover
            raise DataSourceError(f"CSV ファイルが見つかりません: {path}") from exc
        cached = self._month_cache.get(key)
        if cached and cached[1] == mtime:
            return cached[0].copy()
        df = self.load(year=year, month=month)
        self._month_cache[key] = (df, mtime)
        return df.copy()

    def load_many(self, months: Sequence[MonthTuple]) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for y, m in months:
            frames.append(self.load_month(y, m))
        if not frames:
            raise DataSourceError("対象月が指定されていません")
        return pd.concat(frames, ignore_index=True)

    def iter_available_months(self) -> Generator[MonthTuple, None, None]:
        pattern = re.compile(r"収入・支出詳細_(\d{4})-(\d{2})-01_")
        detected: set[MonthTuple] = set()
        for path in self._config.src_dir.glob("収入・支出詳細_*.csv"):
            match = pattern.match(path.name)
            if match:
                detected.add((int(match.group(1)), int(match.group(2))))
        for year, month in sorted(detected):
            yield year, month

    def category_hierarchy(self, *, year: int | None = None, month: int | None = None) -> dict[str, list[str]]:
        if year is None or month is None:
            months = list(self.iter_available_months())
            if not months:
                raise DataSourceError("利用可能な月がありません")
            year, month = months[-1]
        df = self.load_month(year, month)
        groups: dict[str, list[str]] = {}
        for name, group in df.groupby("大項目", observed=False):
            mids = sorted(group["中項目"].dropna().astype(str).unique())
            groups[str(name)] = mids
        return groups

    @staticmethod
    def _resolve_src_dir(src_dir: str | Path) -> Path:
        base_path = Path(src_dir).expanduser().resolve()
        if not base_path.exists():
            raise DataSourceError(f"データディレクトリが見つかりません: {base_path}")
        if not base_path.is_dir():
            raise DataSourceError(f"データディレクトリがディレクトリではありません: {base_path}")
        return base_path

    @staticmethod
    def _make_filename(year: int, month: int) -> str:
        end_day = calendar.monthrange(year, month)[1]
        return f"収入・支出詳細_{year}-{month:02d}-01_{year}-{month:02d}-{end_day:02d}.csv"

    @staticmethod
    def _read_csv(path: Path) -> pd.DataFrame:
        try:
            return pd.read_csv(path, encoding=ENCODING)
        except FileNotFoundError as exc:
            raise DataSourceError(f"CSV ファイルが見つかりません: {path}") from exc

    @staticmethod
    def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.rename(columns={alias: canonical for alias, canonical in COLUMN_ALIASES.items() if alias in df.columns})
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise DataSourceError(f"必要な列が不足しています: {', '.join(sorted(missing))}")
        for column in CATEGORY_COLUMNS:
            if column not in df.columns:
                raise DataSourceError(f"カテゴリ列 {column} が存在しません")
        df["計算対象"] = pd.to_numeric(df["計算対象"], errors="coerce").astype("Int64")
        df["金額（円）"] = pd.to_numeric(df["金額（円）"], errors="coerce").astype("Int64")
        df["日付"] = pd.to_datetime(df["日付"], errors="coerce")
        if df["日付"].isna().any():
            raise DataSourceError("日付列に解析できない値が含まれています")
        df["年月"] = df["日付"].dt.to_period("M").dt.to_timestamp()
        df["年月キー"] = df["日付"].dt.strftime("%Y-%m")
        df["大項目"] = df["大項目"].fillna("未分類").astype("string")
        df["中項目"] = df["中項目"].fillna("未分類").astype("string")
        df["カテゴリ"] = df["大項目"]
        df["大項目"] = df["大項目"].astype("category")
        df["中項目"] = df["中項目"].astype("category")
        return df

    def _post_process(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._normalize_columns(df)
        df = df.loc[(df["計算対象"] == 1) & (df["金額（円）"] < 0)].copy()
        df.sort_values(["日付", "大項目", "中項目"], inplace=True)
        df.reset_index(drop=True, inplace=True)
        return df

    def clear_cache(self) -> None:
        self._month_cache.clear()

    def cache_size(self) -> int:
        return len(self._month_cache)


def month_csv_path(year: int, month: int, src_dir: str = "data") -> Path:
    return HouseholdDataLoader(src_dir).month_csv_path(year, month)


def load_csv_from_month(year: Optional[int], month: Optional[int], src_dir: str = "data") -> pd.DataFrame:  # pragma: no cover
    return HouseholdDataLoader(src_dir).load(year=year, month=month)


def load_csv_for_months(months: Sequence[MonthTuple], src_dir: str = "data") -> pd.DataFrame:  # pragma: no cover
    return HouseholdDataLoader(src_dir).load_many(months)


def iter_available_months(src_dir: str = "data") -> Iterable[MonthTuple]:  # pragma: no cover
    return HouseholdDataLoader(src_dir).iter_available_months()

 
__all__ = [
    "HouseholdDataLoader",
    "LoaderConfig",
    "month_csv_path",
    "load_csv_from_month",
    "load_csv_for_months",
    "iter_available_months",
]
