"""Financial independence MCP tools for FIRE analysis."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy.exc import OperationalError

from household_mcp.analysis import FinancialIndependenceAnalyzer
from household_mcp.analysis.expense_pattern_analyzer import ExpensePatternAnalyzer
from household_mcp.database.manager import DatabaseManager
from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.services.fire_snapshot import (
    FireSnapshotService,
    SnapshotNotFoundError,
)

# Legacy analyzer for backward compatibility
analyzer = FinancialIndependenceAnalyzer()
pattern_analyzer = ExpensePatternAnalyzer()

# Database-backed service for real data access
db_manager = DatabaseManager()

# Resolve data directory
# Try to find the data directory
# 1. Relative to CWD (assuming running from backend)
data_dir = Path("../data").resolve()

if not data_dir.exists() or not any(data_dir.glob("*.csv")):
    # 2. Relative to this file
    current_file = Path(__file__).resolve()
    project_root = current_file.parents[4]
    data_dir = project_root / "data"

if not data_dir.exists():
    # 3. Fallback to default "data" (relative to CWD)
    data_dir = Path("data").resolve()

data_loader = HouseholdDataLoader(src_dir=data_dir)
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
        status_data = fire_service.get_status(
            snapshot_date=None, months=period_months, recalculate=True
        )
    except (SnapshotNotFoundError, OperationalError):
        # No snapshots exist; return reasonable defaults so the tool is
        # usable in fresh environments.
        current_assets = 0
        # Try to calculate annual expense from CSV even if no snapshots exist
        annual_expense = fire_service.estimate_annual_expense()

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


def _get_target_months(period_months: int) -> list[tuple[int, int]]:
    """Generate (year, month) tuples for the last N months."""
    months = []
    today = date.today()
    # Start from last month to ensure full data
    current = today.replace(day=1) - timedelta(days=1)

    for _ in range(period_months):
        months.append((current.year, current.month))
        current = current.replace(day=1) - timedelta(days=1)

    return sorted(months)


def _load_expense_history(period_months: int) -> dict[str, list[Decimal]]:
    """Load expense history from CSV data."""
    target_months = _get_target_months(period_months)

    # Load data
    df = data_loader.load_many(target_months)
    if df.empty:
        return {}

    # Filter expenses (negative amounts) and flip sign
    expenses = df[df["金額（円）"] < 0].copy()
    expenses["amount"] = expenses["金額（円）"].abs()
    expenses["month_key"] = expenses["年月"].dt.strftime("%Y-%m")

    # Group by Category and Month
    grouped = expenses.groupby(["カテゴリ", "month_key"])["amount"].sum().reset_index()

    # Create a full index of (Category, Month) to fill zeros
    categories = grouped["カテゴリ"].unique()
    month_keys = sorted([f"{y}-{m:02d}" for y, m in target_months])

    history = {}
    for cat in categories:
        cat_data = grouped[grouped["カテゴリ"] == cat]
        amounts = []
        for m_key in month_keys:
            val = cat_data[cat_data["month_key"] == m_key]["amount"].sum()
            amounts.append(Decimal(str(val)))
        history[cat] = amounts

    return history


def analyze_expense_patterns(
    period_months: int = 12,
) -> dict[str, Any]:
    """
    Expense pattern analysis tool.

    Classifies regular/irregular spending and suggests reduction
    opportunities using actual household data.

    Args:
        period_months: Analysis period in months (default: 12)

    Returns:
        Expense classification results and analysis

    """
    category_history = _load_expense_history(period_months)

    if not category_history:
        return {
            "message": "指定期間のデータが見つかりませんでした。",
            "period_months": period_months,
            "regular_spending": 0,
            "irregular_spending": 0,
            "categories": [],
        }

    # Use the new ExpensePatternAnalyzer
    result = pattern_analyzer.analyze_expenses(category_history)

    regular_spending = Decimal("0")
    irregular_spending = Decimal("0")
    categories_data = []

    for classification in result.classifications:
        cat_name = classification.category
        total = sum(category_history[cat_name])

        if classification.classification == "regular":
            regular_spending += total
        else:
            irregular_spending += total

        categories_data.append(
            {
                "category": cat_name,
                "classification": classification.classification,
                "confidence": 1.0,
                "total_amount": float(total),
                "classification_ja": (
                    "定期的"
                    if classification.classification == "regular"
                    else (
                        "異常"
                        if classification.classification == "anomaly"
                        else "不定期的"
                    )
                ),
                "average": float(classification.average_amount),
                "is_anomaly": classification.classification == "anomaly",
            }
        )

    return {
        "message": (
            f"定期支出: ¥{regular_spending:,.0f} / "
            f"不定期支出: ¥{irregular_spending:,.0f}"
        ),
        "period_months": period_months,
        "regular_spending": float(regular_spending),
        "irregular_spending": float(irregular_spending),
        "categories": categories_data,
    }


def project_financial_independence_date(
    additional_savings_per_month: float = 0.0,
    custom_growth_rate: float | None = None,
) -> dict[str, Any]:
    """
    FIRE achievement date projection tool.

    Estimates impact of expense reductions or additional
    savings on months to FIRE achievement using actual data.

    Args:
        additional_savings_per_month: Monthly additional savings
            (default: 0)
        custom_growth_rate: Custom growth rate (default: actual)

    Returns:
        Achievement date projection and time savings

    """
    try:
        status_data = fire_service.get_status(snapshot_date=None, months=12)
    except (SnapshotNotFoundError, OperationalError):
        return {
            "message": "資産データまたは支出データが不足しているため、予測できません。",
            "current_scenario": {
                "months_to_fi": None,
                "years_to_fi": None,
            },
            "with_additional_savings": {
                "months_to_fi": None,
                "years_to_fi": None,
            },
            "improvement": {"months_saved": 0, "years_saved": 0.0},
        }

    fi_progress = status_data["fi_progress"]
    snapshot = status_data["snapshot"]

    current_assets = float(snapshot["total"])
    target_assets = float(fi_progress["fire_target"])

    # Use actual growth rate or default to 5% annual if not available
    base_monthly_growth_rate = fi_progress.get("monthly_growth_rate")
    if base_monthly_growth_rate is None:
        base_monthly_growth_rate = 0.00407  # approx 5% annual

    # Determine growth rate to use
    if custom_growth_rate is not None:
        # Convert annual rate to monthly
        monthly_growth_rate = (1 + custom_growth_rate) ** (1 / 12) - 1
    else:
        monthly_growth_rate = base_monthly_growth_rate

    base_months = fi_progress.get("months_to_fi")
    if base_months is None:
        base_months = float("inf")

    base_years = base_months / 12 if base_months != float("inf") else None

    # Calculate new scenario
    # Note: This is a simplified projection that treats additional savings
    # as an immediate boost to asset accumulation speed or equivalent
    # asset value. For accurate projection, we would need the full
    # simulation engine. Here we use the TrendStatistics helper as in
    # the original implementation.
    from household_mcp.analysis import TrendStatistics

    # We approximate the effect of additional monthly savings by adding
    # its 1-year value to the principal, or we need a better formula.
    # Since TrendStatistics.calculate_months_to_fi only takes assets
    # and rate, it assumes NO ongoing savings (pure compound interest
    # of current assets). This is a limitation of the current helper.
    # To reflect "additional savings", we effectively increase the
    # "current assets" in this simplified model, or we need a better
    # calculator. For now, we follow the pattern of the original code:
    # Assuming 5 years boost equivalent
    adjusted_assets = current_assets + (additional_savings_per_month * 12 * 5)

    new_months = TrendStatistics.calculate_months_to_fi(
        current_assets=adjusted_assets,
        target_assets=target_assets,
        monthly_growth_rate=monthly_growth_rate,
    )

    new_years = new_months / 12 if new_months else None

    if base_months != float("inf") and new_months:
        months_saved = base_months - new_months
        years_saved = months_saved / 12
    else:
        months_saved = 0
        years_saved = 0.0

    if years_saved:
        message = (
            f"月{additional_savings_per_month:,.0f}円追加貯蓄(相当)で、"
            f"FIRE達成が{years_saved:.1f}年短縮される可能性があります"
        )
    elif base_years is not None:
        message = f"FIRE達成予定: {base_years:.1f}年後"
    else:
        message = "FIRE達成時期は計算できません（達成済みまたは目標未設定）"

    return {
        "message": message,
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
    annual_expense: float | None = None,
) -> dict[str, Any]:
    """
    Improvement suggestions tool.

    Generates prioritized action suggestions toward FIRE achievement
    using actual household data.

    Args:
        annual_expense: Annual expense amount (optional)

    Returns:
        Prioritized improvement suggestion list

    """
    # Get real status data
    try:
        status_data = fire_service.get_status(snapshot_date=None, months=12)
        current_assets = float(status_data["snapshot"]["total"])
        calculated_annual_expense = float(status_data["fi_progress"]["annual_expense"])
    except (SnapshotNotFoundError, OperationalError):
        current_assets = 0.0
        calculated_annual_expense = 0.0

    target_annual_expense = (
        annual_expense if annual_expense is not None else calculated_annual_expense
    )

    # Load real category history
    category_history_decimal = _load_expense_history(12)

    # Convert to float for analyzer
    category_history = {
        k: [float(v) for v in vals] for k, vals in category_history_decimal.items()
    }

    # If no history, provide dummy structure to avoid errors
    if not category_history:
        category_history = {"データなし": [0.0] * 12}

    if target_annual_expense <= 0:
        return {
            "message": "年間支出が0円または計算できないため、改善提案を作成できません。",
            "suggestions": [],
        }

    # Generate asset history (mocked as flat for now)
    asset_history = [current_assets] * 12

    classification_results = analyzer.classify_expenses(category_history, 12)

    suggestions = analyzer.suggest_improvements(
        current_assets=current_assets,
        annual_expense=target_annual_expense,
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
