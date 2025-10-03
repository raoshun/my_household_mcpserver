"""Trend analysis helpers for household spending data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional, Sequence, Tuple

import pandas as pd

from ..dataloader import HouseholdDataLoader
from ..exceptions import AnalysisError, DataSourceError
from ..utils.query_parser import TrendQuery

MonthTuple = Tuple[int, int]


@dataclass(frozen=True)
class TrendMetrics:
    """Aggregated metrics for a (category, month) pair."""

    category: str
    month: date
    amount: int
    month_over_month: Optional[float]
    year_over_year: Optional[float]
    moving_average: Optional[float]


class CategoryTrendAnalyzer:
    """Aggregate household CSV data into monthly trend metrics.

    DI 対応: 既存の `src_dir` だけでなく、任意の ``HouseholdDataLoader`` を
    直接注入できるようにしテスト容易性・柔軟性を高める。
    互換性: 旧来の ``CategoryTrendAnalyzer(src_dir=...)`` も引き続き利用可能。
    """

    def __init__(self, *, src_dir: str = "data", loader: HouseholdDataLoader | None = None) -> None:
        # 優先: 明示的に渡された loader / フォールバック: src_dir から新規作成
        self._loader: HouseholdDataLoader = loader or HouseholdDataLoader(src_dir)
        self._cache: dict[Tuple[MonthTuple, ...], pd.DataFrame] = {}
        self._cache_signature: dict[Tuple[MonthTuple, ...], Tuple[Tuple[str, float], ...]] = {}

    # 互換用プロパティ
    @property
    def src_dir(self) -> str:
        # 互換用公開アクセサ
        return str(self._loader.src_dir)

    def metrics_for_query(self, query: TrendQuery) -> List[TrendMetrics]:
        """Return metrics for the given query parameters."""

        month_pairs = self._expand_months(query.start, query.end)
        metrics_df = self._get_aggregated(month_pairs)

        if query.category:
            metrics_df = metrics_df[metrics_df["category"] == query.category]
            if metrics_df.empty:
                raise AnalysisError(f"カテゴリ {query.category!r} のデータが見つかりません")

        return self._to_metrics(metrics_df)

    def metrics_for_category(
        self,
        months: Sequence[MonthTuple],
        category: Optional[str] = None,
    ) -> List[TrendMetrics]:
        """Return metrics for the given month list and optional category."""

        month_pairs = self._normalize_months(months)
        metrics_df = self._get_aggregated(month_pairs)

        if category:
            metrics_df = metrics_df[metrics_df["category"] == category]
            if metrics_df.empty:
                raise AnalysisError(f"カテゴリ {category!r} のデータが見つかりません")

        return self._to_metrics(metrics_df)

    def top_categories(
        self,
        months: Sequence[MonthTuple],
        top_n: int = 3,
    ) -> List[str]:
        """Return the top-N categories by total spending for specified months."""

        month_pairs = self._normalize_months(months)
        metrics_df = self._get_aggregated(month_pairs)

        totals = (
            metrics_df.groupby("category", as_index=False)["amount"].sum()
            .sort_values("amount")
        )
        # 金額は負の値（支出）なので、絶対値降順で上位カテゴリを決定
        totals["abs_amount"] = totals["amount"].abs()
        top = totals.sort_values("abs_amount", ascending=False).head(top_n)
        return top["category"].tolist()

    def _get_aggregated(self, months: Tuple[MonthTuple, ...]) -> pd.DataFrame:
        signature = self._compute_signature(months)

        cached = self._cache.get(months)
        cached_signature = self._cache_signature.get(months)
        if cached is not None and cached_signature == signature:
            return cached.copy()
        # Loader DI 経由でロード (内部で HouseholdDataLoader の月次キャッシュ活用)
        df = self._loader.load_many(months)
        if df.empty:
            raise AnalysisError("指定された期間のデータが存在しません")

        aggregated = self._aggregate_dataframe(df)
        self._cache[months] = aggregated
        self._cache_signature[months] = signature
        return aggregated.copy()

    @staticmethod
    def _aggregate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        grouped = (
            df.groupby(["年月", "カテゴリ"], as_index=False)["金額（円）"].sum()
            .rename(columns={"カテゴリ": "category", "金額（円）": "amount"})
        )
        if grouped.empty:
            raise AnalysisError("集計対象のデータがありません")

        grouped.sort_values(["category", "年月"], inplace=True)

        grouped["month_key"] = grouped["年月"].dt.strftime("%Y-%m")
        grouped["month_over_month"] = (
            grouped.groupby("category")["amount"].pct_change()
        )
        grouped["moving_average"] = (
            grouped.groupby("category")["amount"].transform(
                lambda s: s.rolling(window=12, min_periods=1).mean()
            )
        )
        grouped["year_over_year"] = (
            grouped.groupby("category")["amount"].pct_change(periods=12)
        )

        return grouped

    @staticmethod
    def _to_metrics(df: pd.DataFrame) -> List[TrendMetrics]:
        metrics: List[TrendMetrics] = []
        for _, row in df.iterrows():
            month_ts = row["年月"]
            if pd.isna(month_ts):  # pragma: no cover - defensive guard
                continue
            month_date = month_ts.to_pydatetime().date()
            metrics.append(
                TrendMetrics(
                    category=str(row["category"]),
                    month=month_date,
                    amount=int(row["amount"]),
                    month_over_month=(
                        float(row["month_over_month"]) if pd.notna(row["month_over_month"]) else None
                    ),
                    year_over_year=(
                        float(row["year_over_year"]) if pd.notna(row["year_over_year"]) else None
                    ),
                    moving_average=(
                        float(row["moving_average"]) if pd.notna(row["moving_average"]) else None
                    ),
                )
            )
        return metrics

    @staticmethod
    def _normalize_months(months: Sequence[MonthTuple]) -> Tuple[MonthTuple, ...]:
        if not months:
            raise AnalysisError("月の一覧が指定されていません")
        normalized = tuple(sorted((int(year), int(month)) for year, month in months))
        return normalized

    @staticmethod
    def _expand_months(start: date, end: date) -> Tuple[MonthTuple, ...]:
        if start > end:
            raise AnalysisError("開始月は終了月より前である必要があります")

        months: List[MonthTuple] = []
        year, month = start.year, start.month
        while True:
            months.append((year, month))
            if year == end.year and month == end.month:
                break
            month += 1
            if month > 12:
                month = 1
                year += 1
        return tuple(months)

    def clear_cache(self) -> None:
        """Invalidate cached aggregated DataFrames."""

        self._cache.clear()
        self._cache_signature.clear()

    def cache_size(self) -> int:
        """Return the number of cached month combinations."""

        return len(self._cache)

    def _compute_signature(self, months: Tuple[MonthTuple, ...]) -> Tuple[Tuple[str, float], ...]:
        """Return a signature based on CSV paths and their modification times."""

        signature: list[Tuple[str, float]] = []
        for year, month in months:
            try:
                path = self._loader.month_csv_path(year, month)
                stat = path.stat()
            except FileNotFoundError as exc:
                raise DataSourceError(f"CSV ファイルが見つかりません: {path}") from exc
            except DataSourceError:
                raise
            except Exception as exc:  # pragma: no cover - defensive guard
                raise DataSourceError(f"CSV 署名計算中にエラーが発生しました: {exc}") from exc

            signature.append((str(path), stat.st_mtime))

        return tuple(signature)
