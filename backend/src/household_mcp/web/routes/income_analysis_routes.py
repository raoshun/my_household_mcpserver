"""収入分析・貯蓄率・不動産キャッシュフロー REST APIルート."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query

from household_mcp.tools.phase16_tools import (
    generate_comprehensive_cashflow_report,
    get_annual_income_summary,
    get_income_summary,
    get_real_estate_cashflow,
    get_savings_rate,
    get_savings_rate_trend,
)

router = APIRouter(prefix="/api/v1", tags=["income-analysis"])


# ==================== 収入分析エンドポイント ====================


@router.get("/income/{year}/{month}")
async def get_monthly_income(
    year: int = Path(..., ge=2000, le=2100, description="年"),
    month: int = Path(..., ge=1, le=12, description="月"),
) -> dict[str, Any]:
    """
    月次収入サマリーを取得.

    Args:
        year: 年
        month: 月

    Returns:
        収入サマリー辞書

    """
    try:
        return get_income_summary(year, month)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/income/{year}")
async def get_annual_income(
    year: int = Path(..., ge=2000, le=2100, description="年"),
) -> dict[str, Any]:
    """
    年次収入サマリーを取得.

    Args:
        year: 年

    Returns:
        年次収入サマリー辞書

    """
    try:
        return get_annual_income_summary(year)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== 貯蓄率エンドポイント ====================


@router.get("/savings-rate/{year}/{month}")
async def get_monthly_savings_rate(
    year: int = Path(..., ge=2000, le=2100, description="年"),
    month: int = Path(..., ge=1, le=12, description="月"),
) -> dict[str, Any]:
    """
    月次貯蓄率を取得.

    Args:
        year: 年
        month: 月

    Returns:
        貯蓄率辞書

    """
    try:
        return get_savings_rate(year, month)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/savings-rate/trend")
async def get_savings_rate_trend_data(
    start_date: str = Query(..., description="開始日（YYYY-MM-DD）"),
    end_date: str = Query(..., description="終了日（YYYY-MM-DD）"),
) -> dict[str, Any]:
    """
    貯蓄率推移を取得.

    Args:
        start_date: 開始日
        end_date: 終了日

    Returns:
        貯蓄率推移辞書

    """
    try:
        return get_savings_rate_trend(start_date, end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== 不動産キャッシュフローエンドポイント ====================


@router.get("/real-estate-cashflow")
async def get_real_estate_cashflow_data(
    start_date: str = Query(..., description="開始日（YYYY-MM-DD）"),
    end_date: str = Query(..., description="終了日（YYYY-MM-DD）"),
    property_id: str | None = Query(
        default=None, description="物件ID（省略時は全物件合計）"
    ),
) -> dict[str, Any]:
    """
    不動産キャッシュフローを取得.

    Args:
        start_date: 開始日
        end_date: 終了日
        property_id: 物件ID

    Returns:
        キャッシュフロー辞書

    """
    try:
        return get_real_estate_cashflow(start_date, end_date, property_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== 総合レポートエンドポイント ====================


@router.get("/cashflow-report/{year}")
async def get_cashflow_report(
    year: int = Path(..., ge=2000, le=2100, description="年"),
    format: str = Query(default="markdown", description="出力形式（markdown/json）"),
) -> dict[str, Any]:
    """
    年次総合キャッシュフローレポートを取得.

    Args:
        year: 年
        format: 出力形式

    Returns:
        レポート辞書

    """
    try:
        return generate_comprehensive_cashflow_report(year, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
