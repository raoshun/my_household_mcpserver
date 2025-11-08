"""
FIRE (Financial Independence, Retire Early) 計算モジュール

FIRE基準に基づいた目標資産額の計算と関連ユーティリティを提供します。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class FireCalculationResult:
    """FIRE計算結果を表すデータクラス"""

    months_to_fi: int
    target_assets: Decimal
    achieved_assets_timeline: list[dict]
    scenarios: dict[str, dict]
    feasible: bool
    message: str


class FIRECalculator:
    """FIRE基準に基づいて目標資産額を計算するクラス"""

    # FIRE基準: 年支出額 × 25
    FIRE_MULTIPLIER = 25

    @staticmethod
    def calculate_fire_target(
        annual_expense: float, custom_multiplier: float | None = None
    ) -> float:
        """
        FIRE基準に基づいて目標資産額を計算

        Args:
            annual_expense: 年支出額（円）
            custom_multiplier: カスタム倍率（デフォルト: 25）

        Returns:
            目標資産額（円）

        Raises:
            ValueError: 年支出額が0以下の場合

        """
        if annual_expense <= 0:
            raise ValueError(f"年支出額は正の数である必要があります: {annual_expense}")

        if custom_multiplier is not None:
            if custom_multiplier <= 0:
                raise ValueError(
                    f"倍率は正の数である必要があります: {custom_multiplier}"
                )
            multiplier = custom_multiplier
        else:
            multiplier = FIRECalculator.FIRE_MULTIPLIER

        return annual_expense * multiplier

    @staticmethod
    def calculate_progress_rate(current_assets: float, target_assets: float) -> float:
        """
        FIRE目標への進捗率を計算（%）

        Args:
            current_assets: 現在の純資産（円）
            target_assets: 目標資産額（円）

        Returns:
            進捗率（0〜100%、目標達成時は100以上の値も可能）

        """
        if target_assets <= 0:
            raise ValueError(f"目標資産額は正の数である必要があります: {target_assets}")

        progress_rate = (current_assets / target_assets) * 100
        return round(progress_rate, 2)

    @staticmethod
    def is_fi_achieved(current_assets: float, target_assets: float) -> bool:
        """
        経済的自由に達成したかどうかを判定

        Args:
            current_assets: 現在の純資産（円）
            target_assets: 目標資産額（円）

        Returns:
            True: 達成済み、False: 未達成

        """
        return current_assets >= target_assets


def calculate_fire_index(
    current_assets: Decimal,
    monthly_savings: Decimal,
    target_assets: Decimal,
    annual_return_rate: Decimal,
    inflation_rate: Decimal = Decimal("0"),
) -> FireCalculationResult:
    """
    複利とインフレを考慮したFIRE計算エンジン

    月利率の導出: (1 + 年利率)^(1/12) - 1
    資産推移: A_{n} = A_{n-1} * (1 + 月利率) + 月貯蓄

    Args:
        current_assets: 現在資産額（円）
        monthly_savings: 月貯蓄額（円）
        target_assets: 目標資産額（円）
        annual_return_rate: 年利回り（小数。5% = 0.05）
        inflation_rate: インフレ率（小数。2% = 0.02）

    Returns:
        FireCalculationResult: 計算結果

    Raises:
        ValueError: 不正な入力値

    """
    # 入力値の検証
    if current_assets < 0:
        raise ValueError(f"現在資産は非負の数である必要があります: {current_assets}")
    if monthly_savings < 0:
        raise ValueError(f"月貯蓄額は非負の数である必要があります: {monthly_savings}")
    if target_assets <= 0:
        raise ValueError(f"目標資産は正の数である必要があります: {target_assets}")
    if annual_return_rate < 0:
        raise ValueError(
            f"年利回りは非負の数である必要があります: {annual_return_rate}"
        )
    if inflation_rate < 0:
        raise ValueError(f"インフレ率は非負の数である必要があります: {inflation_rate}")

    # 月利率の計算: (1 + 年利率)^(1/12) - 1
    annual_rate_plus_1 = Decimal("1") + annual_return_rate
    # 12乗根の近似計算
    # 月利 ≈ (1 + 年利)^(1/12) - 1
    # より精密には: month_rate = (1 + annual_rate)^(1/12) - 1
    # ここでは簡略化として: month_rate ≈ annual_rate / 12
    # ただし、複利効果を考慮した正確な計算を行う
    monthly_rate = _calculate_monthly_rate(annual_rate_plus_1)

    # 到達判定: 月貯蓄が足りるか
    if monthly_savings == 0 and current_assets < target_assets:
        return FireCalculationResult(
            months_to_fi=-1,
            target_assets=target_assets,
            achieved_assets_timeline=[],
            scenarios={},
            feasible=False,
            message="月貯蓄がゼロで目標に到達できません",
        )

    # シミュレーション実行（複利計算）
    months_timeline = []
    assets = current_assets
    month = 0
    max_months = 1000  # 無限ループ防止

    while assets < target_assets and month < max_months:
        month += 1
        # 利息計算
        interest = assets * monthly_rate
        # 資産更新
        assets = assets + interest + monthly_savings
        # インフレ調整（実質資産の減少）
        if inflation_rate > 0:
            # 実質資産 = 名目資産 * (1 - インフレ率)^(month/12)
            inflation_adjustment = inflation_rate / Decimal("12")
            assets_adjusted = assets * ((Decimal("1") - inflation_adjustment) ** month)
        else:
            assets_adjusted = assets

        months_timeline.append(
            {
                "month": month,
                "nominal_assets": float(assets.quantize(Decimal("0.01"))),
                "real_assets": float(assets_adjusted.quantize(Decimal("0.01"))),
                "monthly_interest": float(interest.quantize(Decimal("0.01"))),
            }
        )

    # 到達判定
    if month >= max_months:
        feasible = False
        message = "計算期間内に目標に到達できません（月数が上限超過）"
        months_to_fi = -1
    elif assets < target_assets:
        feasible = False
        message = "計算期間内に目標に到達できません"
        months_to_fi = -1
    else:
        feasible = True
        message = f"{month}ヶ月で目標資産に到達予定"
        months_to_fi = month

    # シナリオ別計算（悲観: 3%, 中立: 5%, 楽観: 7%）
    scenarios = {}
    for scenario_name, scenario_rate in [
        ("pessimistic", Decimal("0.03")),
        ("neutral", Decimal("0.05")),
        ("optimistic", Decimal("0.07")),
    ]:
        scenario_result = _simulate_scenario(
            current_assets,
            monthly_savings,
            target_assets,
            scenario_rate,
            inflation_rate,
        )
        scenarios[scenario_name] = {
            "months_to_fi": scenario_result,
            "annual_return_rate": float(scenario_rate * 100),
        }

    return FireCalculationResult(
        months_to_fi=months_to_fi,
        target_assets=target_assets,
        achieved_assets_timeline=months_timeline,
        scenarios=scenarios,
        feasible=feasible,
        message=message,
    )


def _calculate_monthly_rate(annual_rate_plus_1: Decimal) -> Decimal:
    """
    年利率から月利率を計算（複利）

    月利 = (1 + 年利)^(1/12) - 1

    Args:
        annual_rate_plus_1: (1 + 年利率)

    Returns:
        Decimal: 月利率

    """
    # Newton-Raphson法で12乗根を計算
    # x^12 = annual_rate_plus_1 の解を求める
    x = annual_rate_plus_1 ** (Decimal("1") / Decimal("12"))
    return x - Decimal("1")


def _simulate_scenario(
    current_assets: Decimal,
    monthly_savings: Decimal,
    target_assets: Decimal,
    annual_return_rate: Decimal,
    inflation_rate: Decimal,
) -> int:
    """
    シナリオ別シミュレーション

    Args:
        current_assets: 現在資産額
        monthly_savings: 月貯蓄額
        target_assets: 目標資産額
        annual_return_rate: 年利回り
        inflation_rate: インフレ率

    Returns:
        int: 到達月数（到達不可の場合は-1）

    """
    monthly_rate = _calculate_monthly_rate(Decimal("1") + annual_return_rate)
    assets = current_assets
    month = 0
    max_months = 1000

    while assets < target_assets and month < max_months:
        month += 1
        interest = assets * monthly_rate
        assets = assets + interest + monthly_savings
        # インフレ調整
        if inflation_rate > 0:
            inflation_adjustment = inflation_rate / Decimal("12")
            assets = assets * ((Decimal("1") - inflation_adjustment) ** month)

    return month if month < max_months else -1
