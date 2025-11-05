"""
経済的自由度分析REST APIエンドポイント

FIRE進捗追跡、シナリオ投影、支出分類、改善提案に関するエンドポイント
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from household_mcp.analysis import FinancialIndependenceAnalyzer

router = APIRouter(prefix="/api/financial-independence", tags=["FIRE"])

# 分析器の初期化（シングルトン風）
analyzer = FinancialIndependenceAnalyzer()


@router.get("/status")
async def get_financial_independence_status(
    period_months: int = Query(
        12,
        ge=1,
        le=120,
        description="分析期間（月数、1-120ヶ月）",
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
        # TODO: 実際のデータソースから取得
        # ここではダミーデータを使用
        current_assets = 5000000
        annual_expense = 1000000
        asset_history = [5000000 + (i * 50000) for i in range(period_months)]

        status = analyzer.get_status(
            current_assets=current_assets,
            target_assets=25000000,
            annual_expense=annual_expense,
            asset_history=asset_history,
        )

        return {
            "timestamp": None,
            "period_months": period_months,
            "fire_percentage": status["progress_rate"],
            "target_amount": status["fire_target"],
            "current_assets": status["current_assets"],
            "monthly_growth_rate": (
                status["growth_analysis"]["monthly_growth_rate"]
                if status["growth_analysis"]
                else None
            ),
            "annual_growth_rate": (
                status["growth_analysis"]["annual_growth_rate"]
                if status["growth_analysis"]
                else None
            ),
            "months_to_fi": status["months_to_fi"],
            "is_achieved": status["is_achieved"],
            "progress_details": status,
        }

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
        asset_history = [5000000 + (i * 50000) for i in range(period_months)]

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
            "食費": [50000 + (i * 100) for i in range(period_months)],
            "交通費": [5000 if i % 2 == 0 else 0 for i in range(period_months)],
            "医療費": [200000 if i == 5 else 0 for i in range(period_months)],
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
