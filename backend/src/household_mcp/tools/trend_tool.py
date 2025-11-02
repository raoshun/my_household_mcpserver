"""MCP tool helpers for category trend analysis."""

from __future__ import annotations

from datetime import date
from typing import Any

from ..analysis import CategoryTrendAnalyzer
from ..dataloader import iter_available_months, load_csv_from_month
from ..exceptions import DataSourceError
from ..utils import (
    format_category_trend_response,
    resolve_trend_query,
    trend_metrics_to_dict,
)

MonthTuple = tuple[int, int]
AnalyzerCache = dict[str, CategoryTrendAnalyzer]

_DEFAULT_SRC_DIR = "data"
_ANALYZERS: AnalyzerCache = {}


def _get_analyzer(src_dir: str = _DEFAULT_SRC_DIR) -> CategoryTrendAnalyzer:
    analyzer = _ANALYZERS.get(src_dir)
    if analyzer is None:
        analyzer = CategoryTrendAnalyzer(src_dir=src_dir)
        _ANALYZERS[src_dir] = analyzer
    return analyzer


def _list_available_months(src_dir: str = _DEFAULT_SRC_DIR) -> list[MonthTuple]:
    months = list(iter_available_months(src_dir=src_dir))
    if not months:
        raise DataSourceError("利用可能な月が見つかりません")
    return months


def _available_categories(src_dir: str = _DEFAULT_SRC_DIR) -> list[str]:
    months = _list_available_months(src_dir)
    latest_year, latest_month = months[-1]
    df = load_csv_from_month(latest_year, latest_month, src_dir=src_dir)
    if df.empty:
        raise DataSourceError("カテゴリ情報を取得できませんでした")
    return sorted({str(cat) for cat in df["大項目"].astype(str).unique()})


def _month_pairs(start: date, end: date) -> tuple[MonthTuple, ...]:
    months: list[MonthTuple] = []
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


def category_trend_summary(
    *,
    src_dir: str = _DEFAULT_SRC_DIR,
    window: int = 12,
    top_n: int = 3,
) -> dict[str, Any]:
    """Return category trend metrics summary for the latest window."""

    months = _list_available_months(src_dir)
    target_months = months[-window:] if len(months) > window else months
    analyzer = _get_analyzer(src_dir)

    top_categories = analyzer.top_categories(target_months, top_n=top_n)
    summary = {
        category: trend_metrics_to_dict(
            analyzer.metrics_for_category(target_months, category=category)
        )
        for category in top_categories
    }

    return {
        "months": [{"year": y, "month": m} for y, m in target_months],
        "top_categories": top_categories,
        "metrics": summary,
    }


def get_category_trend(
    *,
    category: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
    src_dir: str = _DEFAULT_SRC_DIR,
    top_n: int = 3,
    default_window: int = 12,
) -> dict[str, Any]:
    """Return a formatted trend analysis for the requested category/month range."""

    months = _list_available_months(src_dir)
    available_months_dict = [{"year": y, "month": m} for y, m in months]
    available_categories = _available_categories(src_dir)

    query = resolve_trend_query(
        category=category,
        start_month=start_month,
        end_month=end_month,
        available_months=available_months_dict,
        available_categories=available_categories,
        default_window=default_window,
    )

    analyzer = _get_analyzer(src_dir)
    month_pairs = _month_pairs(query.start, query.end)

    if query.category:
        metrics = analyzer.metrics_for_query(query)
        return {
            "category": query.category,
            "start_month": query.start.strftime("%Y-%m"),
            "end_month": query.end.strftime("%Y-%m"),
            "text": format_category_trend_response(query.category, metrics),
            "metrics": trend_metrics_to_dict(metrics),
        }

    top_categories = analyzer.top_categories(month_pairs, top_n=top_n)
    details = []
    for cat in top_categories:
        metrics = analyzer.metrics_for_category(month_pairs, category=cat)
        details.append(
            {
                "category": cat,
                "text": format_category_trend_response(cat, metrics),
                "metrics": trend_metrics_to_dict(metrics),
            }
        )

    return {
        "category": None,
        "start_month": query.start.strftime("%Y-%m"),
        "end_month": query.end.strftime("%Y-%m"),
        "top_categories": top_categories,
        "details": details,
    }
