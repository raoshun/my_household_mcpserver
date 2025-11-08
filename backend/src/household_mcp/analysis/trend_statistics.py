"""
トレンド統計分析モジュール

月次成長率の計算、シナリオ投影、FIRE達成までの月数計算を提供します。
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np
from scipy import stats


class GrowthRateAnalysis(NamedTuple):
    """成長率分析結果"""

    monthly_growth_rate: float  # 月間成長率（%）
    growth_rate_decimal: float  # 月間成長率（小数形式）
    annual_growth_rate: float  # 年間成長率（%）
    confidence: float  # 信頼度（0.0-1.0）
    data_points: int  # 分析に使用したデータポイント数
    r_squared: float  # R二乗値（0.0-1.0）


class ProjectionScenario(NamedTuple):
    """投影シナリオ結果"""

    scenario_name: str
    growth_rate: float  # 月間成長率（小数形式）
    current_assets: float
    target_assets: float
    months_to_fi: float | None  # 達成までの月数（不可能な場合はNone）
    projected_assets_12m: float  # 12ヶ月後の予想資産
    projected_assets_60m: float  # 60ヶ月後の予想資産
    is_achievable: bool  # 達成可能かどうか


class TrendStatistics:
    """
    トレンド統計分析クラス

    月次成長率の計算、成長トレンドの分析、FIRE達成までの
    月数計算を行います。
    """

    # 最小データポイント数
    MIN_DATA_POINTS = 3

    @staticmethod
    def calculate_monthly_growth_rate(
        asset_values: list[float], method: str = "regression"
    ) -> GrowthRateAnalysis:
        """
        月次成長率を計算

        Args:
            asset_values: 月次資産額のリスト（時系列順）
            method: 計算方法 ("regression" or "average")
                - "regression": 線形回帰で長期トレンド抽出
                - "average": 直前月比の平均

        Returns:
            GrowthRateAnalysis: 成長率分析結果

        """
        if len(asset_values) < TrendStatistics.MIN_DATA_POINTS:
            raise ValueError(
                f"最少{TrendStatistics.MIN_DATA_POINTS}個のデータポイントが必要です"
            )

        if method == "regression":
            return TrendStatistics._calculate_by_regression(asset_values)
        elif method == "average":
            return TrendStatistics._calculate_by_average(asset_values)
        else:
            raise ValueError(f"未知の計算方法: {method}")

    @staticmethod
    def _calculate_by_regression(
        asset_values: list[float],
    ) -> GrowthRateAnalysis:
        """線形回帰による月次成長率計算"""
        x = np.arange(len(asset_values))
        y = np.array(asset_values)

        # 線形回帰実行
        slope, _intercept, r_value, _p_value, _std_err = stats.linregress(x, y)

        # 成長率に変換
        # 初月資産を基準に計算
        if asset_values[0] == 0:
            monthly_growth_decimal = 0.0
            monthly_growth_percent = 0.0
        else:
            # 月間成長を成長率に変換
            monthly_growth_decimal = slope / asset_values[0]
            monthly_growth_percent = monthly_growth_decimal * 100

        # 年間成長率（複利計算）
        annual_growth_percent = ((1 + monthly_growth_decimal) ** 12 - 1) * 100

        # 信頼度 = R二乗値
        confidence = r_value**2

        return GrowthRateAnalysis(
            monthly_growth_rate=float(round(monthly_growth_percent, 4)),
            growth_rate_decimal=float(round(monthly_growth_decimal, 6)),
            annual_growth_rate=float(round(annual_growth_percent, 2)),
            confidence=float(round(confidence, 3)),
            data_points=len(asset_values),
            r_squared=float(round(confidence, 3)),
        )

    @staticmethod
    def _calculate_by_average(asset_values: list[float]) -> GrowthRateAnalysis:
        """月次成長率の直前比平均計算"""
        growth_rates = []

        for i in range(1, len(asset_values)):
            if asset_values[i - 1] == 0:
                continue
            rate = (asset_values[i] - asset_values[i - 1]) / asset_values[i - 1]
            growth_rates.append(rate)

        if not growth_rates:
            monthly_growth_decimal = 0.0
            monthly_growth_percent = 0.0
            confidence = 0.0
        else:
            monthly_growth_decimal = np.mean(growth_rates)
            monthly_growth_percent = monthly_growth_decimal * 100
            # 信頼度 = データ点数と変動性に基づく
            mean_val = np.mean(growth_rates)
            if mean_val != 0:
                cv = np.std(growth_rates) / abs(mean_val)
            else:
                cv = 0
            confidence = max(0.0, 1.0 - cv)

        annual_growth_percent = ((1 + monthly_growth_decimal) ** 12 - 1) * 100

        return GrowthRateAnalysis(
            monthly_growth_rate=float(round(monthly_growth_percent, 4)),
            growth_rate_decimal=float(round(monthly_growth_decimal, 6)),
            annual_growth_rate=float(round(annual_growth_percent, 2)),
            confidence=float(round(confidence, 3)),
            data_points=len(growth_rates),
            r_squared=float(round(confidence, 3)),
        )

    @staticmethod
    def calculate_months_to_fi(
        current_assets: float, target_assets: float, monthly_growth_rate: float
    ) -> float | None:
        """
        FIRE達成までの月数を計算

        式: n = log(目標資産 / 現在資産) / log(1 + 月間成長率)

        Args:
            current_assets: 現在の資産額
            target_assets: 目標資産額
            monthly_growth_rate: 月間成長率（小数形式）

        Returns:
            達成までの月数（達成不可能な場合はNone）

        """
        if current_assets < 0 or target_assets < 0:
            raise ValueError("資産額は0以上である必要があります")

        if current_assets == 0 and monthly_growth_rate <= 0:
            return None

        if target_assets <= current_assets:
            return 0.0

        if monthly_growth_rate <= 0:
            return None

        # 成長率から月数を計算
        try:
            months = math.log(target_assets / current_assets) / math.log(
                1 + monthly_growth_rate
            )
            return round(months, 2)
        except (ValueError, ZeroDivisionError):
            return None

    @staticmethod
    def project_assets(
        current_assets: float, monthly_growth_rate: float, months: int
    ) -> float:
        """
        複利計算で未来の資産を投影

        式: 未来資産 = 現在資産 × (1 + 月間成長率) ^ 月数

        Args:
            current_assets: 現在の資産額
            monthly_growth_rate: 月間成長率（小数形式）
            months: 投影対象月数

        Returns:
            投影資産額

        """
        if current_assets < 0:
            raise ValueError("現在の資産額は0以上である必要があります")

        if months < 0:
            raise ValueError("月数は0以上である必要があります")

        projected = current_assets * ((1 + monthly_growth_rate) ** months)
        return round(projected, 2)

    @staticmethod
    def create_projection_scenario(
        scenario_name: str,
        current_assets: float,
        target_assets: float,
        monthly_growth_rate: float,
    ) -> ProjectionScenario:
        """
        投影シナリオを作成

        Args:
            scenario_name: シナリオ名（例: "悲観的", "中立的", "楽観的"）
            current_assets: 現在の資産額
            target_assets: 目標資産額
            monthly_growth_rate: 月間成長率（小数形式）

        Returns:
            ProjectionScenario: 投影結果

        """
        months_to_fi = TrendStatistics.calculate_months_to_fi(
            current_assets, target_assets, monthly_growth_rate
        )

        projected_12m = TrendStatistics.project_assets(
            current_assets, monthly_growth_rate, 12
        )

        projected_60m = TrendStatistics.project_assets(
            current_assets, monthly_growth_rate, 60
        )

        is_achievable = months_to_fi is not None

        return ProjectionScenario(
            scenario_name=scenario_name,
            growth_rate=round(monthly_growth_rate, 6),
            current_assets=current_assets,
            target_assets=target_assets,
            months_to_fi=months_to_fi,
            projected_assets_12m=projected_12m,
            projected_assets_60m=projected_60m,
            is_achievable=is_achievable,
        )

    @staticmethod
    def calculate_moving_average(values: list[float], window: int = 3) -> list[float]:
        """
        単純移動平均を計算

        Args:
            values: 値のリスト
            window: 移動平均ウィンドウサイズ

        Returns:
            移動平均値のリスト（元の長さ）

        """
        if window <= 0 or window > len(values):
            raise ValueError(f"ウィンドウサイズは1〜{len(values)}である必要があります")

        ma = np.convolve(values, np.ones(window) / window, mode="valid")

        # 元の長さに合わせるため、最初の値を補充
        padding = [values[0]] * (len(values) - len(ma))
        return padding + list(ma)
