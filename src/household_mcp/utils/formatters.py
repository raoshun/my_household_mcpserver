"""Formatting helpers for trend-related output."""

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Optional, Union, Any, Dict

NumberLike = Union[int, float, Decimal]


def _to_decimal(value: NumberLike | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid numeric value: {value!r}") from exc


def format_currency(value: Optional[NumberLike], unit: str = "円") -> str:
    if value is None:
        return "N/A"
    amount = _to_decimal(value).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return f"{amount:,.0f}{unit}"


def format_percentage(value: Optional[NumberLike], digits: int = 1) -> str:
    if value is None:
        return "N/A"
    number = _to_decimal(value)
    if number.is_nan():
        return "N/A"
    quant = Decimal(f"1.{'0' * digits}")
    percentage = (number * Decimal(100)).quantize(quant, rounding=ROUND_HALF_UP)
    return f"{percentage:.{digits}f}%"


def trend_metrics_to_dict(metrics: Any) -> Dict[str, Any]:
    try:
        return asdict(metrics)  # dataclass support
    except TypeError:
        return dict(metrics.__dict__)


def format_category_trend_response(category: str, metrics: Any) -> dict[str, Any]:
    data = trend_metrics_to_dict(metrics)
    formatted = {
        "category": category,
        "total_spent": format_currency(data.get("total_spent")),
        "month_over_month": format_percentage(data.get("mom_change")),
        "year_over_year": format_percentage(data.get("yoy_change")),
        "moving_average": format_currency(data.get("moving_average")),
        "months": data.get("months"),
    }
    return formatted


__all__ = [
    "format_currency",
    "format_percentage",
    "format_category_trend_response",
    "trend_metrics_to_dict",
]
