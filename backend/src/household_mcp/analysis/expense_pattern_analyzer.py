"""
支出パターン分析・異常検知モジュール

定期支出・変動支出・異常支出を自動分類し、季節性とトレンドを検出します。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import mean, stdev
from typing import Literal

import numpy as np
from scipy import stats


@dataclass
class ExpenseClassification:
    """支出分類結果"""

    category: str
    classification: Literal["regular", "variable", "anomaly"]
    average_amount: Decimal
    variance: Decimal
    std_deviation: Decimal
    data_points: int


@dataclass
class SeasonalityAnalysis:
    """季節性分析結果"""

    category: str
    monthly_indices: dict[int, float]
    has_seasonality: bool
    peak_month: int
    trough_month: int


@dataclass
class TrendAnalysis:
    """トレンド分析結果"""

    category: str
    slope: float
    intercept: float
    r_squared: float
    trend_direction: Literal["increasing", "decreasing", "flat"]


@dataclass
class ExpensePatternResult:
    """支出パターン分析結果"""

    classifications: list[ExpenseClassification]
    seasonality: list[SeasonalityAnalysis]
    trends: list[TrendAnalysis]
    analysis_period_months: int


class ExpensePatternAnalyzer:
    """支出パターン分析エンジン"""

    MIN_DATA_POINTS = 3
    REGULAR_EXPENSE_VARIANCE_THRESHOLD = Decimal("5")  # 5% variance
    ANOMALY_THRESHOLD_SIGMA = 2  # 平均 + 2σ

    def __init__(self):
        """初期化"""
        pass

    def analyze_expenses(
        self, expense_data: dict[str, list[Decimal]]
    ) -> ExpensePatternResult:
        """
        支出パターン分析

        Args:
            expense_data: カテゴリ別月別支出データ
                         {"カテゴリ名": [月1, 月2, ..., 月N]}

        Returns:
            支出パターン分析結果

        """
        classifications = []
        seasonality_list = []
        trends = []

        for category, amounts in expense_data.items():
            if len(amounts) < self.MIN_DATA_POINTS:
                # データ不足
                continue

            # 分類
            classification = self._classify_expense(category, amounts)
            classifications.append(classification)

            # 季節性分析
            if len(amounts) >= 12:
                season = self._analyze_seasonality(category, amounts)
                seasonality_list.append(season)

            # トレンド分析
            if len(amounts) >= 3:
                trend = self._analyze_trend(category, amounts)
                trends.append(trend)

        return ExpensePatternResult(
            classifications=classifications,
            seasonality=seasonality_list,
            trends=trends,
            analysis_period_months=len(next(iter(expense_data.values()))),
        )

    def _classify_expense(
        self, category: str, amounts: list[Decimal]
    ) -> ExpenseClassification:
        """
        支出を分類（定期/変動/異常）

        Args:
            category: カテゴリ名
            amounts: 月別支出額

        Returns:
            分類結果

        """
        amounts_float = [float(a) for a in amounts]

        avg = Decimal(str(mean(amounts_float)))
        if len(amounts_float) > 1:
            std = Decimal(str(stdev(amounts_float)))
        else:
            std = Decimal("0")

        # 変動率の計算（平均に対する標準偏差の割合）
        if avg > 0:
            variance_pct = (std / avg) * Decimal("100")
        else:
            variance_pct = Decimal("0")

        # 分類判定
        if variance_pct < self.REGULAR_EXPENSE_VARIANCE_THRESHOLD:
            classification = "regular"
        else:
            classification = "variable"

        return ExpenseClassification(
            category=category,
            classification=classification,
            average_amount=avg,
            variance=variance_pct,
            std_deviation=std,
            data_points=len(amounts),
        )

    def _analyze_seasonality(
        self, category: str, amounts: list[Decimal]
    ) -> SeasonalityAnalysis:
        """
        季節性分析（12ヶ月データ前提）

        Args:
            category: カテゴリ名
            amounts: 月別支出額

        Returns:
            季節性分析結果

        """
        # 12ヶ月単位での平均を計算
        monthly_sums = [Decimal("0")] * 12
        monthly_counts = [0] * 12

        for i, amount in enumerate(amounts):
            month_idx = i % 12
            monthly_sums[month_idx] += amount
            monthly_counts[month_idx] += 1

        # 月別平均
        monthly_averages = [
            (
                monthly_sums[i] / monthly_counts[i]
                if monthly_counts[i] > 0
                else Decimal("0")
            )
            for i in range(12)
        ]

        # 全体平均
        overall_avg = sum(monthly_averages) / Decimal(12)

        # 月別指数（100 = 平均）
        monthly_indices = {}
        for i, avg in enumerate(monthly_averages):
            if overall_avg > 0:
                index = (avg / overall_avg) * 100
            else:
                index = 100
            monthly_indices[i + 1] = float(index)

        # 季節性判定（最大値と最小値の差が20%以上）
        indices_values = list(monthly_indices.values())
        max_idx = max(indices_values)
        min_idx = min(indices_values)
        seasonality_range = max_idx - min_idx

        has_seasonality = seasonality_range >= 20

        # ピークと谷
        get_func = monthly_indices.get
        peak_month = max(monthly_indices, key=get_func)  # type: ignore
        trough_month = min(monthly_indices, key=get_func)  # type: ignore

        return SeasonalityAnalysis(
            category=category,
            monthly_indices=monthly_indices,
            has_seasonality=has_seasonality,
            peak_month=peak_month,
            trough_month=trough_month,
        )

    def _analyze_trend(self, category: str, amounts: list[Decimal]) -> TrendAnalysis:
        """
        トレンド分析（線形回帰）

        Args:
            category: カテゴリ名
            amounts: 月別支出額

        Returns:
            トレンド分析結果

        """
        amounts_float = np.array([float(a) for a in amounts])
        x = np.arange(len(amounts_float))

        # 線形回帰
        result = stats.linregress(x, amounts_float)
        slope_val: float = result.slope  # type: ignore
        intercept_val: float = result.intercept  # type: ignore
        r_value: float = result.rvalue  # type: ignore

        r_squared = r_value**2

        # トレンド判定
        if slope_val > 0.5:  # 閾値: 月0.5円以上の増加
            trend_direction = "increasing"
        elif slope_val < -0.5:  # 月0.5円以上の減少
            trend_direction = "decreasing"
        else:
            trend_direction = "flat"

        return TrendAnalysis(
            category=category,
            slope=slope_val,
            intercept=intercept_val,
            r_squared=float(r_squared),
            trend_direction=trend_direction,
        )

    @staticmethod
    def detect_anomalies(
        expense_data: dict[str, list[Decimal]],
        sigma_threshold: float = 2.0,
    ) -> dict[str, list[int]]:
        """
        異常値検出（平均 + σ_threshold * 標準偏差を超える値）

        Args:
            expense_data: カテゴリ別月別支出データ
            sigma_threshold: シグマ閾値（デフォルト: 2）

        Returns:
            {カテゴリ: [異常月インデックスリスト]}

        """
        anomalies = {}

        for category, amounts in expense_data.items():
            if len(amounts) < 3:
                continue

            amounts_float = [float(a) for a in amounts]
            avg = mean(amounts_float)
            std = stdev(amounts_float)

            threshold = avg + sigma_threshold * std
            anomaly_indices = [
                i for i, amount in enumerate(amounts_float) if amount > threshold
            ]

            if anomaly_indices:
                anomalies[category] = anomaly_indices

        return anomalies
