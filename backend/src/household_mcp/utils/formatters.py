"""Formatting helpers for trend-related output."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import TYPE_CHECKING, Union

NumberLike = Union[int, float, Decimal]

if TYPE_CHECKING:  # pragma: no cover
    from ..analysis.trends import TrendMetrics


def _to_decimal(value: NumberLike | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid numeric value: {value!r}") from exc


def format_currency(value: NumberLike | None, unit: str = "円") -> str:
    """
    Format a numeric value as currency.

    Args:
        value: Numeric value to format, or None.
        unit: Currency unit symbol (default: 円).

    Returns:
        Formatted currency string with thousand separators, or "N/A" if value is None.

    """
    if value is None:
        return "N/A"
    amount = _to_decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{amount:,.0f}{unit}"


def format_percentage(value: NumberLike | None, digits: int = 1) -> str:
    """
    Format a numeric value as percentage.

    Args:
        value: Numeric value to format (as decimal, e.g., 0.15 = 15%), or None.
        digits: Number of decimal places to display (default: 1).

    Returns:
        Formatted percentage string, or "N/A" if value is None or NaN.

    """
    if value is None:
        return "N/A"
    number = _to_decimal(value)
    if number.is_nan():
        return "N/A"
    quant = Decimal(f"1.{'0' * digits}")
    percentage = (number * Decimal(100)).quantize(quant, rounding=ROUND_HALF_UP)
    return f"{percentage:.{digits}f}%"


def format_category_trend_response(
    category: str,
    metrics: Sequence[TrendMetrics],
    *,
    include_average: bool = True,
) -> str:
    """
    カテゴリのトレンドを自然言語要約として整形する。

    期待フォーマット（テスト参照）:
    "食費の 2025年06月〜2025年07月 の推移です。\n- 2025年06月: 6,000円 （前月比 N/A, 前年同月比 N/A, 12か月平均 6,000円)\n..."
    """

    if not metrics:
        return f"{category} の対象データが見つかりませんでした。"

    start = metrics[0].month
    end = metrics[-1].month
    lines: list[str] = [f"{category}の {start:%Y年%m月}〜{end:%Y年%m月} の推移です。"]

    for metric in metrics:
        amount_text = format_currency(abs(metric.amount))
        mom_text = (
            format_percentage(metric.month_over_month)
            if metric.month_over_month is not None
            else "N/A"
        )
        yoy_text = (
            format_percentage(metric.year_over_year)
            if metric.year_over_year is not None
            else "N/A"
        )
        avg_value = (
            abs(metric.moving_average)
            if include_average and metric.moving_average is not None
            else None
        )
        avg_text = format_currency(avg_value) if include_average else ""

        detail = f"- {metric.month:%Y年%m月}: {amount_text} （前月比 {mom_text}, 前年同月比 {yoy_text}"
        if include_average:
            detail += f", 12か月平均 {avg_text}"
        detail += ")"
        lines.append(detail)

    return "\n".join(lines)


def trend_metrics_to_dict(metrics: Sequence[TrendMetrics]) -> list[dict[str, object]]:
    """TrendMetrics シーケンスをシリアライズ可能な辞書リストへ変換。"""

    rows: list[dict[str, object]] = []
    for metric in metrics:
        rows.append(
            {
                "category": metric.category,
                "month": metric.month.strftime("%Y-%m"),
                "amount": metric.amount,
                "month_over_month": metric.month_over_month,
                "year_over_year": metric.year_over_year,
                "moving_average": metric.moving_average,
            }
        )
    return rows


__all__ = [
    "format_category_trend_response",
    "format_currency",
    "format_percentage",
    "trend_metrics_to_dict",
]
