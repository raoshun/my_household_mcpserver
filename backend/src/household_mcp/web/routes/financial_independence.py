"""
経済的自由度分析REST APIエンドポイント

FIRE進捗追跡、シナリオ投影、支出分類、改善提案に関するエンドポイント
"""

from __future__ import annotations

from datetime import date as dt_date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from household_mcp.analysis import FinancialIndependenceAnalyzer
from household_mcp.database.manager import DatabaseManager
from household_mcp.services.fire_snapshot import (
    FireSnapshotRequest,
    FireSnapshotService,
    SnapshotNotFoundError,
)
from household_mcp.tools.analysis_tools import (
    simulate_fire_scenarios,
    what_if_fire_simulation,
)

router = APIRouter(prefix="/api/financial-independence", tags=["FIRE"])

# 分析器の初期化（シングルトン風）
analyzer = FinancialIndependenceAnalyzer()


def _get_snapshot_service() -> FireSnapshotService:
    """FireSnapshotService を生成（DB初期化は冪等）。"""
    db = DatabaseManager()
    # 必要に応じてテーブル作成（冪等）
    db.initialize_database()
    return FireSnapshotService(db_manager=db)


@router.get("/status")
async def get_financial_independence_status(
    period_months: int = Query(
        12,
        ge=1,
        le=120,
        description="分析期間（月数、1-120ヶ月）",
    ),
    snapshot_date: str | None = Query(
        None,
        description="対象日（YYYY-MM-DD、省略時は最新）",
    ),
) -> dict[str, Any]:
    """
    現在のFIREプログレス状態を取得

    Returns:
        - fire_percentage: FIRE到達率（%）
        - target_amount: 目標資産額（円）
        - current_assets: 現在の資産額（円）
        - monthly_growth_rate: 月間成長率（%）
        - annual_growth_rate: 年間成長率（%）
        - months_to_fi: FIRE達成予定月数
        - progress_details: 詳細情報

    """
    try:
        service = _get_snapshot_service()
        target_date = None
        if snapshot_date:
            try:
                year, month, day = (int(x) for x in snapshot_date.split("-"))
                target_date = dt_date(year, month, day)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=(f"日付形式が不正です: {exc!s}"),
                )

        result = service.get_status(
            snapshot_date=target_date,
            months=period_months,
        )
        snapshot = result.get("snapshot", {})
        fi = result.get("fi_progress", {})
        growth_rate = fi.get("monthly_growth_rate")

        return {
            "timestamp": snapshot.get("snapshot_date"),
            "period_months": period_months,
            "fire_percentage": fi.get("progress_rate"),
            "target_amount": fi.get("fire_target"),
            "current_assets": fi.get("current_assets"),
            "monthly_growth_rate": growth_rate,
            "annual_growth_rate": None,  # 年率は未算出（必要なら変換）
            "months_to_fi": fi.get("months_to_fi"),
            "is_achieved": fi.get("is_achievable"),
            "progress_details": {
                "snapshot": snapshot,
                "fi_progress": fi,
                "history": result.get("history", []),
            },
        }

    except SnapshotNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"FIRE状態取得エラー: {e!s}",
        ) from e


@router.get("/projections")
async def get_financial_independence_projections(
    period_months: int = Query(12, ge=1, le=120, description="投影期間（月数）"),
) -> dict[str, Any]:
    """
    複数シナリオによるFIRE達成予測を取得

    Returns:
        scenarios: [
            {
                "scenario_name": "シナリオ名",
                "growth_rate": 月間成長率,
                "months_to_fi": 達成月数,
                "projected_12m": 12ヶ月後資産,
                "projected_60m": 60ヶ月後資産,
                "is_achievable": 達成可能性
            }
        ]

    """
    try:
        # TODO: 実際のデータソースから取得
        current_assets = 5000000
        annual_expense = 1000000
        asset_history = [float(5000000 + (i * 50000)) for i in range(period_months)]

        scenarios = analyzer.calculate_scenarios(
            current_assets=current_assets,
            annual_expense=annual_expense,
            asset_history=asset_history,
        )

        return {
            "timestamp": None,
            "current_assets": current_assets,
            "fire_target": 25000000,
            "scenarios": [
                {
                    "scenario_name": s.scenario_name,
                    "growth_rate": s.growth_rate,
                    "current_assets": s.current_assets,
                    "target_assets": s.target_assets,
                    "months_to_fi": s.months_to_fi,
                    "projected_assets_12m": s.projected_assets_12m,
                    "projected_assets_60m": s.projected_assets_60m,
                    "is_achievable": s.is_achievable,
                }
                for s in scenarios
            ],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"シナリオ投影エラー: {e!s}",
        ) from e


@router.get("/expense-breakdown")
async def get_expense_breakdown(
    period_months: int = Query(12, ge=1, le=120, description="分析期間（月数）"),
) -> dict[str, Any]:
    """
    支出の定期的/不定期的分類結果を取得

    Returns:
        categories: [
            {
                "category": "カテゴリ名",
                "classification": "regular|irregular",
                "confidence": 信頼度,
                "total_amount": 合計金額,
                "average_amount": 平均金額,
                "occurrence_rate": 発生頻度
            }
        ]

    """
    try:
        # TODO: 実際のデータソースから取得
        category_history = {
            "食費": [float(50000 + (i * 100)) for i in range(period_months)],
            "交通費": [float(5000 if i % 2 == 0 else 0) for i in range(period_months)],
            "医療費": [float(200000 if i == 5 else 0) for i in range(period_months)],
        }

        classification_results = analyzer.classify_expenses(
            category_history, period_months
        )

        categories = []
        for cat_name, result in classification_results.items():
            amounts = category_history[cat_name]
            non_zero = [a for a in amounts if a > 0]
            categories.append(
                {
                    "category": cat_name,
                    "classification": result.classification,
                    "confidence": result.confidence,
                    "total_amount": sum(amounts),
                    "average_amount": (
                        sum(non_zero) / len(non_zero) if non_zero else 0
                    ),
                    "occurrence_rate": len(non_zero) / period_months,
                    "reasoning": result.reasoning,
                }
            )

        return {
            "timestamp": None,
            "period_months": period_months,
            "categories": categories,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"支出分類エラー: {e!s}",
        ) from e


@router.post("/update-expense-classification")
async def update_expense_classification(
    category: str = Query(..., description="支出カテゴリ"),
    classification: str = Query(..., description="分類（regular|irregular）"),
) -> dict[str, Any]:
    """
    支出分類をユーザーが手動上書き

    Args:
        category: 支出カテゴリ名
        classification: 手動設定の分類

    Returns:
        更新結果

    """
    try:
        if classification not in ["regular", "irregular"]:
            raise ValueError("分類は 'regular' または 'irregular' である必要があります")

        # TODO: データベースに保存
        return {
            "status": "success",
            "category": category,
            "classification": classification,
            "message": f"{category} を {classification} に分類しました",
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"分類更新エラー: {e!s}",
        ) from e


# Asset management endpoints


class AssetRecord(BaseModel):
    """資産レコードのデータ構造"""

    year: int
    month: int
    asset_type: str
    amount: float


@router.post("/add-asset")
async def add_asset(asset: AssetRecord) -> dict[str, Any]:
    """
    資産レコードを追加

    Args:
        asset: AssetRecord (year, month, asset_type, amount)

    Returns:
        追加結果

    """
    try:
        if asset.month < 1 or asset.month > 12:
            raise ValueError("月は1-12である必要があります")
        if asset.amount < 0:
            raise ValueError("金額は0以上である必要があります")

        valid_types = ["cash", "stocks", "funds", "realestate", "pension"]
        if asset.asset_type not in valid_types:
            raise ValueError(f"資産種別は {valid_types} のいずれかである必要があります")

        # TODO: データベースに保存
        # ここではダミー処理

        return {
            "status": "success",
            "message": (
                f"{asset.year}年{asset.month}月の{asset.asset_type}を記録しました"
            ),
            "asset_type": asset.asset_type,
            "amount": asset.amount,
            "record_date": f"{asset.year}-{asset.month:02d}",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"資産追加エラー: {e!s}",
        ) from e


@router.delete("/delete-asset")
async def delete_asset(asset: AssetRecord) -> dict[str, Any]:
    """
    資産レコードを削除

    Args:
        asset: AssetRecord (year, month, asset_type)

    Returns:
        削除結果

    """
    try:
        if asset.month < 1 or asset.month > 12:
            raise ValueError("月は1-12である必要があります")

        valid_types = ["cash", "stocks", "funds", "realestate", "pension"]
        if asset.asset_type not in valid_types:
            raise ValueError(f"資産種別は {valid_types} のいずれかである必要があります")

        # TODO: データベースから削除
        # ここではダミー処理

        return {
            "status": "success",
            "message": (
                f"{asset.year}年{asset.month}月の{asset.asset_type}を削除しました"
            ),
            "record_date": f"{asset.year}-{asset.month:02d}",
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"資産削除エラー: {e!s}",
        ) from e


# --- FIRE Snapshot Endpoints ---


@router.post("/snapshot")
async def register_fire_snapshot(
    request: FireSnapshotRequest,
) -> dict[str, Any]:
    """FIRE資産スナップショットを登録（同日付は上書き）。"""
    try:
        service = _get_snapshot_service()
        result = service.register_snapshot(request)
        return {"success": True, "data": result.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"登録エラー: {e!s}") from e


@router.get("/snapshot")
async def get_fire_snapshot(
    snapshot_date: str | None = Query(
        None, description="対象日（YYYY-MM-DD、省略時は最新）"
    ),
    allow_interpolation: bool = Query(
        True, description="未登録日の場合に補完を許可するか"
    ),
) -> dict[str, Any]:
    """指定日のスナップショットを取得（必要に応じて補完）。"""
    try:
        service = _get_snapshot_service()
        target_date = None
        if snapshot_date:
            try:
                y, m, d = (int(x) for x in snapshot_date.split("-"))
                target_date = dt_date(y, m, d)
            except Exception as exc:
                raise HTTPException(
                    status_code=400,
                    detail=(f"日付形式が不正です: {exc!s}"),
                )

        result = service.get_snapshot(
            snapshot_date=target_date, allow_interpolation=allow_interpolation
        )
        return {"success": True, "data": result.model_dump()}
    except SnapshotNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"取得エラー: {e!s}") from e


# ==================== 強化FIREシミュレーション ====================


class FIREScenarioRequest(BaseModel):
    """FIREシナリオリクエスト."""

    name: str = Field(..., description="シナリオ名")
    current_assets: Decimal = Field(..., description="現在資産額（円）")
    monthly_savings: Decimal = Field(..., description="月次貯蓄額（円）")
    annual_expense: Decimal = Field(..., description="年間支出額（円）")
    annual_return_rate: Decimal = Field(..., description="年利回り（小数）")
    fire_type: str = Field(..., description="FIREタイプ（STANDARD/COAST/BARISTA/SIDE）")
    inflation_rate: Decimal = Field(default=Decimal("0"), description="インフレ率")
    passive_income: Decimal = Field(default=Decimal("0"), description="不労所得")
    part_time_income: Decimal | None = Field(
        default=None, description="パート収入（BARISTA）"
    )
    side_income: Decimal | None = Field(default=None, description="副業収入（SIDE）")


class FIREScenariosRequest(BaseModel):
    """複数シナリオ一括シミュレーションリクエスト."""

    scenarios: list[FIREScenarioRequest] = Field(
        ..., max_length=5, description="シナリオリスト（最大5件）"
    )


class WhatIfRequest(BaseModel):
    """What-If分析リクエスト."""

    base_scenario: FIREScenarioRequest = Field(..., description="ベースシナリオ")
    changes: dict[str, Decimal] = Field(
        ..., description="変更パラメータ（monthly_savings, annual_return_rate等）"
    )


@router.post("/scenarios")
async def simulate_fire(request: FIREScenariosRequest) -> dict[str, Any]:
    """
    複数シナリオを一括シミュレーション.

    Args:
        request: シナリオリクエスト

    Returns:
        シミュレーション結果辞書

    """
    try:
        scenarios = [s.model_dump() for s in request.scenarios]
        return simulate_fire_scenarios(scenarios)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/what-if")
async def what_if_fire(request: WhatIfRequest) -> dict[str, Any]:
    """
    What-If分析を実行.

    Args:
        request: What-Ifリクエスト

    Returns:
        影響分析結果辞書

    """
    try:
        base_scenario = request.base_scenario.model_dump()
        changes = {k: v for k, v in request.changes.items()}
        return what_if_fire_simulation(base_scenario, changes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
