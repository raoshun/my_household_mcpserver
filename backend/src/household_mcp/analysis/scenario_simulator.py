"""
シナリオ分析・最適化モジュール

支出削減・収入増加のシナリオを複数比較し、最適な改善施策を推奨します。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .fire_calculator import _simulate_scenario


@dataclass
class ScenarioConfig:
    """シナリオ設定"""

    name: str
    description: str
    expense_reduction_pct: Decimal = Decimal("0")
    income_increase: Decimal = Decimal("0")
    difficulty_score: Decimal = Decimal("1")


@dataclass
class ScenarioResult:
    """シナリオ分析結果"""

    scenario_name: str
    description: str
    original_months_to_fi: int
    scenario_months_to_fi: int
    months_saved: int
    difficulty_score: Decimal
    roi_score: Decimal
    achievable: bool
    message: str


class ScenarioSimulator:
    """シナリオ分析・最適化エンジン"""

    def __init__(
        self,
        current_assets: Decimal,
        current_monthly_savings: Decimal,
        target_assets: Decimal,
        annual_return_rate: Decimal,
        current_monthly_expense: Decimal,
        inflation_rate: Decimal = Decimal("0"),
    ):
        """
        シナリオシミュレーター初期化

        Args:
            current_assets: 現在資産額
            current_monthly_savings: 月貯蓄額
            target_assets: 目標資産額
            annual_return_rate: 年利回り
            current_monthly_expense: 現在月支出額
            inflation_rate: インフレ率

        """
        self.current_assets = current_assets
        self.current_monthly_savings = current_monthly_savings
        self.target_assets = target_assets
        self.annual_return_rate = annual_return_rate
        self.current_monthly_expense = current_monthly_expense
        self.inflation_rate = inflation_rate

        # ベースシナリオの計算
        self.original_months_to_fi = _simulate_scenario(
            current_assets,
            current_monthly_savings,
            target_assets,
            annual_return_rate,
            inflation_rate,
        )

    def simulate_scenarios(
        self, scenarios: list[ScenarioConfig]
    ) -> list[ScenarioResult]:
        """
        複数シナリオをシミュレーション

        Args:
            scenarios: シナリオリスト

        Returns:
            シナリオ分析結果リスト（ROI降順）

        """
        results = []

        for scenario in scenarios:
            result = self._simulate_single_scenario(scenario)
            results.append(result)

        # ROI降順でソート
        results.sort(key=lambda x: x.roi_score, reverse=True)
        return results

    def _simulate_single_scenario(self, scenario: ScenarioConfig) -> ScenarioResult:
        """
        単一シナリオをシミュレーション

        Args:
            scenario: シナリオ設定

        Returns:
            シナリオ分析結果

        """
        # 支出削減による月貯蓄の増加
        expense_reduction = (
            self.current_monthly_expense
            * scenario.expense_reduction_pct
            / Decimal("100")
        )
        income_increase = scenario.income_increase

        # 新しい月貯蓄
        new_monthly_savings = (
            self.current_monthly_savings + expense_reduction + income_increase
        )

        # 削減後の月支出
        reduced_monthly_expense = self.current_monthly_expense - expense_reduction

        # 支出削減の合計が月支出を超える場合の警告
        achievable = True
        message = ""
        if reduced_monthly_expense < 0:
            achievable = False
            message = (
                "警告: 削減後の月支出が負になります "
                f"（削減前: {self.current_monthly_expense}, "
                f"削減後: {reduced_monthly_expense}）"
            )
            # 月支出の上限まで削減
            new_monthly_savings = (
                self.current_monthly_savings + self.current_monthly_expense
            )

        # シナリオで到達月数を計算
        scenario_months_to_fi = _simulate_scenario(
            self.current_assets,
            new_monthly_savings,
            self.target_assets,
            self.annual_return_rate,
            self.inflation_rate,
        )

        # 月数短縮
        if scenario_months_to_fi == -1:
            months_saved = 0
            achievable_scenario = False
            if not message:
                message = "目標資産に到達できません"
        else:
            months_saved = self.original_months_to_fi - scenario_months_to_fi
            achievable_scenario = True

        # ROI計算: 効果 / 難易度
        if scenario.difficulty_score > 0:
            roi_score = Decimal(months_saved) / scenario.difficulty_score
        else:
            roi_score = Decimal("0")

        if not message:
            message = f"{months_saved}ヶ月短縮（難易度: {scenario.difficulty_score}）"

        return ScenarioResult(
            scenario_name=scenario.name,
            description=scenario.description,
            original_months_to_fi=self.original_months_to_fi,
            scenario_months_to_fi=scenario_months_to_fi,
            months_saved=months_saved,
            difficulty_score=scenario.difficulty_score,
            roi_score=roi_score,
            achievable=achievable and achievable_scenario,
            message=message,
        )

    @staticmethod
    def get_recommended_scenario(
        results: list[ScenarioResult],
    ) -> ScenarioResult | None:
        """
        ROIが最も高いシナリオを推奨

        Args:
            results: シナリオ分析結果リスト

        Returns:
            推奨シナリオ（到達不可の場合はNone）

        """
        for result in results:
            if result.achievable:
                return result
        return None

    @staticmethod
    def create_default_scenarios(
        current_monthly_expense: Decimal,
    ) -> list[ScenarioConfig]:
        """
        デフォルトシナリオを生成

        Args:
            current_monthly_expense: 月支出額

        Returns:
            デフォルトシナリオリスト（5個）

        """
        scenarios = [
            ScenarioConfig(
                name="支出削減10%",
                description="全カテゴリ支出を10%削減",
                expense_reduction_pct=Decimal("10"),
                income_increase=Decimal("0"),
                difficulty_score=Decimal("2"),
            ),
            ScenarioConfig(
                name="支出削減20%",
                description="全カテゴリ支出を20%削減",
                expense_reduction_pct=Decimal("20"),
                income_increase=Decimal("0"),
                difficulty_score=Decimal("4"),
            ),
            ScenarioConfig(
                name="収入増加50000円/月",
                description="副業または昇給で月50,000円増加",
                expense_reduction_pct=Decimal("0"),
                income_increase=Decimal("50000"),
                difficulty_score=Decimal("3"),
            ),
            ScenarioConfig(
                name="複合: 支出10% + 収入30000円/月",
                description="支出削減10% + 収入30,000円/月増加",
                expense_reduction_pct=Decimal("10"),
                income_increase=Decimal("30000"),
                difficulty_score=Decimal("2.5"),
            ),
            ScenarioConfig(
                name="積極的: 支出15% + 収入50000円/月",
                description="支出削減15% + 収入50,000円/月増加",
                expense_reduction_pct=Decimal("15"),
                income_increase=Decimal("50000"),
                difficulty_score=Decimal("4.5"),
            ),
        ]
        return scenarios
