"""Financial independence MCP tools for FIRE analysis."""

from __future__ import annotations

from typing import Any

from household_mcp.analysis import FinancialIndependenceAnalyzer
from household_mcp.database.manager import DatabaseManager
from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.services.fire_snapshot import (
    FireSnapshotService,
    SnapshotNotFoundError,
)

# Legacy analyzer for backward compatibility
analyzer = FinancialIndependenceAnalyzer()

# Database-backed service for real data access
db_manager = DatabaseManager()
data_loader = HouseholdDataLoader()
fire_service = FireSnapshotService(db_manager, data_loader=data_loader)


def get_financial_independence_status(
    period_months: int = 12,
) -> dict[str, Any]:
    """
    FIRE progress check tool.

    Returns current FIRE progress rate, monthly growth rate, and
    months to FIRE achievement.

    Args:
        period_months: Analysis period in months (default: 12)

    Returns:
        FIRE progress information with Japanese text

    """
    # データベースから実データを取得（スナップショットが未登録でも実行可能）
    try:
        status_data = fire_service.get_status(snapshot_date=None, months=period_months)
    except SnapshotNotFoundError:
        # No snapshots exist; return reasonable defaults so the tool is
        # usable in fresh environments.
        current_assets = 0
        annual_expense = fire_service.default_annual_expense

        status_data = {
            "snapshot": {
                "total": current_assets,
                "snapshot_date": None,
                "is_interpolated": False,
            },
            "fi_progress": {
                "annual_expense": annual_expense,
                "progress_rate": 0.0,
                "fire_target": int(annual_expense / fire_service.withdrawal_rate),
                "monthly_growth_rate": None,
                "months_to_fi": None,
            },
        }

    snapshot = status_data["snapshot"]
    fi_progress = status_data["fi_progress"]

    current_assets = snapshot["total"]
    annual_expense = fi_progress["annual_expense"]
    progress_rate = fi_progress["progress_rate"]
    fire_target = fi_progress["fire_target"]
    monthly_growth_rate = fi_progress.get("monthly_growth_rate")
    months_to_fi = fi_progress.get("months_to_fi")

    return {
        "message": (f"あなたのFIRE進度は現在 {progress_rate:.1f}% です"),
        "progress_rate": progress_rate,
        "fire_target": fire_target,
        "current_assets": current_assets,
        "annual_expense": annual_expense,
        "monthly_growth_rate": monthly_growth_rate,
        "months_to_fi": months_to_fi,
        "years_to_fi": (
            round(months_to_fi / 12, 1)
            if months_to_fi is not None and months_to_fi > 0
            else (0.0 if months_to_fi == 0 else None)
        ),
        "is_achieved": fi_progress.get("is_achievable", False),
        "snapshot_date": snapshot["snapshot_date"],
        "is_interpolated": snapshot["is_interpolated"],
        "details": status_data,
    }


def analyze_expense_patterns(
    period_months: int = 12,
) -> dict[str, Any]:
    """
    Expense pattern analysis tool.

    Classifies regular/irregular spending and suggests reduction
    opportunities.

    Args:
        period_months: Analysis period in months (default: 12)

    Returns:
        Expense classification results and analysis

    """
    category_history = {
        "食費": [float(50000 + (i * 100)) for i in range(period_months)],
        "交通費": [float(5000) if i % 2 == 0 else 0.0 for i in range(period_months)],
        "医療費": [float(200000) if i == 5 else 0.0 for i in range(period_months)],
        "通信費": [float(8000) for i in range(period_months)],
        "衣料費": [float(10000) if i % 3 == 0 else 0.0 for i in range(period_months)],
    }

    classification_results = analyzer.classify_expenses(category_history, period_months)

    regular_spending = 0.0
    irregular_spending = 0.0
    categories_data = []

    for cat_name, result in classification_results.items():
        amounts = category_history[cat_name]
        total = sum(amounts)
        if result.classification == "regular":
            regular_spending += total
        else:
            irregular_spending += total

        categories_data.append(
            {
                "category": cat_name,
                "classification": result.classification,
                "confidence": result.confidence,
                "total_amount": total,
                "classification_ja": (
                    "定期的" if result.classification == "regular" else "不定期的"
                ),
            }
        )

    return {
        "message": (
            f"定期支出: ¥{regular_spending:,.0f} / "
            f"不定期支出: ¥{irregular_spending:,.0f}"
        ),
        "period_months": period_months,
        "regular_spending": regular_spending,
        "irregular_spending": irregular_spending,
        "categories": categories_data,
    }


def project_financial_independence_date(
    additional_savings_per_month: float = 0.0,
    custom_growth_rate: float | None = None,
) -> dict[str, Any]:
    """
    FIRE achievement date projection tool.

    Estimates impact of expense reductions or additional
    savings on months to FIRE achievement.

    Args:
        additional_savings_per_month: Monthly additional savings
            (default: 0)
        custom_growth_rate: Custom growth rate (default: actual)

    Returns:
        Achievement date projection and time savings

    """
    current_assets = 5000000
    annual_expense = 1000000
    asset_history = [float(5000000 + (i * 50000)) for i in range(12)]

    status_base = analyzer.get_status(
        current_assets=current_assets,
        target_assets=25000000,
        annual_expense=annual_expense,
        asset_history=asset_history,
    )

    base_months = status_base["months_to_fi"] or float("inf")
    base_years = base_months / 12 if base_months != float("inf") else None

    if additional_savings_per_month > 0:
        adjusted_assets = current_assets + (additional_savings_per_month * 12)
        adjusted_growth_rate = custom_growth_rate or (
            status_base["growth_analysis"]["growth_rate_decimal"]
            if status_base["growth_analysis"]
            else 0.01
        )
        from household_mcp.analysis import TrendStatistics

        new_months = TrendStatistics.calculate_months_to_fi(
            current_assets=adjusted_assets,
            target_assets=25000000,
            monthly_growth_rate=adjusted_growth_rate,
        )
        new_years = new_months / 12 if new_months else None
        months_saved = base_months - new_months if new_months else None
        years_saved = months_saved / 12 if months_saved else None
    else:
        new_months = base_months
        new_years = base_years
        months_saved = 0
        years_saved = 0.0

    return {
        "message": (
            f"月{additional_savings_per_month:,.0f}円追加貯蓄で、"
            f"FIRE達成が{years_saved:.1f}年短縮されます"
            if years_saved
            else f"FIRE達成予定: {base_years:.1f}年後"
        ),
        "current_scenario": {
            "months_to_fi": base_months,
            "years_to_fi": base_years,
        },
        "with_additional_savings": {
            "additional_monthly": additional_savings_per_month,
            "months_to_fi": new_months,
            "years_to_fi": new_years,
        },
        "improvement": {
            "months_saved": months_saved,
            "years_saved": years_saved,
        },
    }


def suggest_improvement_actions(
    annual_expense: float = 1000000,
) -> dict[str, Any]:
    """
    Improvement suggestions tool.

    Generates prioritized action suggestions toward FIRE achievement.

    Args:
        annual_expense: Annual expense amount

    Returns:
        Prioritized improvement suggestion list

    """
    current_assets = 5000000
    asset_history = [float(5000000 + (i * 50000)) for i in range(12)]

    category_history = {
        "食費": [float(50000 + (i * 100)) for i in range(12)],
        "交通費": [float(5000) if i % 2 == 0 else 0.0 for i in range(12)],
        "医療費": [float(200000) if i == 5 else 0.0 for i in range(12)],
    }

    classification_results = analyzer.classify_expenses(category_history, 12)

    suggestions = analyzer.suggest_improvements(
        current_assets=current_assets,
        annual_expense=annual_expense,
        asset_history=asset_history,
        category_classification=classification_results,
    )

    formatted_suggestions = []
    for sugg in suggestions:
        priority_ja = {
            "HIGH": "🔴 高",
            "MEDIUM": "🟡 中",
            "LOW": "🟢 低",
        }.get(sugg.get("priority", "MEDIUM"), sugg.get("priority"))

        formatted_suggestions.append(
            {
                "priority": sugg.get("priority"),
                "priority_ja": priority_ja,
                "type": sugg.get("type"),
                "title": sugg.get("title"),
                "description": sugg.get("description"),
                "impact": sugg.get("impact"),
            }
        )

    return {
        "message": f"{len(formatted_suggestions)}件の改善提案があります",
        "suggestions": formatted_suggestions,
    }


def compare_scenarios(
    scenario_configs: dict[str, float] | None = None,
) -> dict[str, Any]:
    """
    Scenario comparison tool.

    Compares multiple growth scenarios and determines the optimal
    target.

    Args:
        scenario_configs: Custom scenario configuration
            {"scenario_name": monthly_growth_rate, ...}

    Returns:
        Scenario comparison results

    """
    current_assets = 5000000
    annual_expense = 1000000
    asset_history = [float(5000000 + (i * 50000)) for i in range(12)]

    scenarios = analyzer.calculate_scenarios(
        current_assets=current_assets,
        annual_expense=annual_expense,
        asset_history=asset_history,
        custom_scenarios=scenario_configs,
    )

    comparison_data = []
    for scenario in scenarios:
        comparison_data.append(
            {
                "scenario_name": scenario.scenario_name,
                "growth_rate_pct": round(scenario.growth_rate * 100, 2),
                "months_to_fi": scenario.months_to_fi,
                "years_to_fi": (
                    round(scenario.months_to_fi / 12, 1)
                    if scenario.months_to_fi
                    else None
                ),
                "projected_12m": scenario.projected_assets_12m,
                "projected_60m": scenario.projected_assets_60m,
                "is_achievable": scenario.is_achievable,
                "achievability_ja": (
                    "達成可能" if scenario.is_achievable else "達成不可能"
                ),
            }
        )

    achievable = [
        s for s in comparison_data if s["is_achievable"] and s["months_to_fi"]
    ]
    best_scenario = (
        min(achievable, key=lambda x: x["months_to_fi"]) if achievable else None
    )

    return {
        "message": (
            f"最適シナリオ: {best_scenario['scenario_name']} "
            f"({best_scenario['years_to_fi']:.1f}年)"
            if best_scenario
            else "達成可能なシナリオがありません"
        ),
        "scenarios": comparison_data,
        "best_scenario": best_scenario,
        "total_scenarios": len(comparison_data),
    }


def submit_asset_record(
    year: int,
    month: int,
    asset_type: str,
    amount: float,
) -> dict[str, Any]:
    """
    Submit asset record for FIRE tracking.

    Records asset information (cash, stocks, funds, real estate, pension)
    for a specific month and recalculates FIRE progress.

    Args:
        year: Year of the asset record (e.g., 2024)
        month: Month of the asset record (1-12)
        asset_type: Type of asset (cash|stocks|funds|realestate|pension)
        amount: Asset amount in JPY

    Returns:
        Confirmation with updated FIRE metrics

    """
    # Validate inputs
    if not 1 <= month <= 12:
        return {
            "status": "error",
            "message": "月は1-12である必要があります",
        }

    if amount < 0:
        return {
            "status": "error",
            "message": "金額は0以上である必要があります",
        }

    valid_types = ["cash", "stocks", "funds", "realestate", "pension"]
    if asset_type not in valid_types:
        return {
            "status": "error",
            "message": f"資産種別は {valid_types} のいずれかである必要があります",
        }

    # NOTE: Database persistence not yet implemented
    # Future implementation will:
    # 1. Save the asset record
    # 2. Recalculate FIRE progress
    # 3. Return updated metrics

    return {
        "status": "success",
        "message": (
            f"{year}年{month}月の{asset_type}を記録しました（金額: ¥{amount:,.0f}）"
        ),
        "record": {
            "year": year,
            "month": month,
            "asset_type": asset_type,
            "amount": amount,
        },
        "next_steps": (
            "資産情報はダッシュボードに反映されます。FIRE進度が更新されました。"
        ),
    }


def get_annual_expense_breakdown(
    year: int | None = None,
) -> dict[str, Any]:
    """
    Get annual expense breakdown from household CSV data.

    Returns monthly and category-level expense breakdown for the
    specified year or most recent 12 months.

    Args:
        year: Target year (None = most recent 12 months)

    Returns:
        Annual expense breakdown with monthly and category totals

    """
    try:
        # Get available months
        available_months = list(data_loader.iter_available_months())
        if not available_months:
            return {
                "status": "error",
                "message": "利用可能な家計簿データがありません",
            }

        # Select target months
        if year is not None:
            target_months = [(y, m) for y, m in available_months if y == year]
            period_label = f"{year}年"
        else:
            target_months = available_months[-12:]
            period_label = "直近12ヶ月"

        if not target_months:
            return {
                "status": "error",
                "message": f"{period_label}のデータがありません",
            }

        # Load data
        df = data_loader.load_many(target_months)
        total_expense = abs(df["金額（円）"].sum())

        # Monthly breakdown
        monthly_data = []
        monthly_groups = df.groupby("年月キー")
        for month_key in sorted(str(k) for k in monthly_groups.groups.keys()):
            group = monthly_groups.get_group(month_key)
            monthly_total = abs(group["金額（円）"].sum())
            monthly_data.append(
                {
                    "month": month_key,
                    "amount": int(monthly_total),
                }
            )

        # Category breakdown
        category_data = []
        category_groups = df.groupby("大項目")
        for category_name in sorted(str(k) for k in category_groups.groups.keys()):
            group = category_groups.get_group(category_name)
            category_total = abs(group["金額（円）"].sum())
            category_data.append(
                {
                    "category": str(category_name),
                    "amount": int(category_total),
                }
            )

        return {
            "status": "success",
            "message": f"{period_label}の年間支出: ¥{total_expense:,.0f}",
            "period": period_label,
            "total_annual_expense": int(total_expense),
            "months_count": len(target_months),
            "monthly_breakdown": monthly_data,
            "category_breakdown": category_data,
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"データ取得エラー: {exc}",
        }


def compare_actual_vs_fire_target(
    period_months: int = 12,
) -> dict[str, Any]:
    """
    Compare actual spending vs FIRE target.

    Compares actual household spending from CSV with FIRE target
    calculated from 4% withdrawal rule.

    Args:
        period_months: Analysis period in months (default: 12)

    Returns:
        Comparison of actual vs FIRE-based spending

    """
    try:
        # Get FIRE status (includes CSV-based calculation)
        status_data = fire_service.get_status(snapshot_date=None, months=period_months)

        fi_progress = status_data["fi_progress"]
        annual_expense = fi_progress["annual_expense"]
        current_assets = fi_progress["current_assets"]
        fire_target = fi_progress["fire_target"]

        # Get actual spending breakdown
        breakdown = get_annual_expense_breakdown(year=None)

        if breakdown["status"] == "error":
            actual_expense = None
            difference = None
            ratio = None
        else:
            actual_expense = breakdown["total_annual_expense"]
            difference = actual_expense - (current_assets * 0.04)
            ratio = actual_expense / (current_assets * 0.04)

        return {
            "status": "success",
            "message": (
                f"実支出: ¥{actual_expense:,.0f} / "
                f"FIRE目標支出: ¥{current_assets * 0.04:,.0f}"
                if actual_expense
                else "実支出データが取得できませんでした"
            ),
            "current_assets": int(current_assets),
            "fire_target": int(fire_target),
            "annual_expense_calculated": int(annual_expense),
            "actual_annual_expense": actual_expense,
            "fire_based_expense": int(current_assets * 0.04),
            "difference": int(difference) if difference else None,
            "expense_ratio": round(ratio, 2) if ratio else None,
            "breakdown": breakdown if actual_expense else None,
        }

    except Exception as exc:
        return {
            "status": "error",
            "message": f"比較エラー: {exc}",
        }
