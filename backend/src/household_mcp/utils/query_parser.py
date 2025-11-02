"""Utilities to resolve natural language-like query inputs into structured parameters."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from ..exceptions import ValidationError

_MONTH_PATTERN = re.compile(r"^(?P<year>\d{4})[\-/年]?(?P<month>\d{1,2})")


@dataclass(frozen=True)
class TrendQuery:
    """Resolved query parameters for trend analysis."""

    category: str | None
    start: date
    end: date

    def month_span(self) -> int:
        """Return the number of months within the span (inclusive)."""

        return (
            (self.end.year - self.start.year) * 12
            + (self.end.month - self.start.month)
            + 1
        )


def to_month_key(year: int, month: int) -> str:
    """Return canonical month key (YYYY-MM)."""

    return f"{year:04d}-{month:02d}"


def _parse_month_string(value: str) -> date:
    match = _MONTH_PATTERN.match(value.strip())
    if not match:
        raise ValidationError(f"月を表す文字列ではありません: {value!r}")

    year = int(match.group("year"))
    month = int(match.group("month"))
    if not (1 <= month <= 12):
        raise ValidationError(f"月は 1〜12 の範囲で指定してください: {value!r}")

    return date(year, month, 1)


def sorted_available_months(
    available_months: Sequence[Mapping[str, int]],
) -> list[date]:
    """Convert available month dictionaries to a sorted list of dates (ascending)."""

    months: set[date] = set()
    for entry in available_months:
        try:
            year = int(entry["year"])
            month = int(entry["month"])
            months.add(date(year, month, 1))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValidationError("available_months の形式が不正です") from exc

    if not months:
        raise ValidationError("利用可能な月の情報が空です")

    return sorted(months)


def _resolve_category(
    category: str | None, available_categories: Iterable[str] | None
) -> str | None:
    if category is None:
        return None

    normalized = category.strip()
    if available_categories is None:
        return normalized or None

    catalog = {item.strip(): item for item in available_categories}
    if normalized not in catalog:
        raise ValidationError(f"カテゴリ {category!r} は利用可能なリストに存在しません")

    return catalog[normalized]


def resolve_trend_query(
    *,
    category: str | None,
    start_month: str | None,
    end_month: str | None,
    available_months: Sequence[Mapping[str, int]],
    available_categories: Iterable[str] | None = None,
    default_window: int = 12,
) -> TrendQuery:
    """
    Resolve raw query parameters to canonical form.

    Args:
        category: Optional category name.
        start_month: Optional string such as "2025-01".
        end_month: Optional string such as "2025-06".
        available_months: Iterable of {"year": int, "month": int} dicts.
        available_categories: Optional catalogue of supported categories.
        default_window: Window length (#months) used when start/end is omitted.

    Returns:
        TrendQuery with normalized values.

    """

    months = sorted_available_months(available_months)
    index_map = {m: idx for idx, m in enumerate(months)}

    resolved_end: date
    resolved_start: date

    if end_month:
        resolved_end = _parse_month_string(end_month)
        if resolved_end not in index_map:
            raise ValidationError(
                f"指定した終了月 {end_month!r} のデータが見つかりません"
            )
    else:
        resolved_end = months[-1]

    if start_month:
        resolved_start = _parse_month_string(start_month)
        if resolved_start not in index_map:
            raise ValidationError(
                f"指定した開始月 {start_month!r} のデータが見つかりません"
            )
    else:
        end_idx = index_map[resolved_end]
        start_idx = max(0, end_idx - default_window + 1)
        resolved_start = months[start_idx]

    # If only start provided, ensure end uses available months ordering.
    if end_month is None:
        end_idx = index_map[resolved_end]
    else:
        end_idx = index_map[resolved_end]

    start_idx = index_map[resolved_start]
    if start_idx > end_idx:
        raise ValidationError("開始月は終了月より前である必要があります")

    resolved_category = _resolve_category(category, available_categories)

    return TrendQuery(
        category=resolved_category, start=resolved_start, end=months[end_idx]
    )
