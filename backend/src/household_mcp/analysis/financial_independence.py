"""
経済的自由度分析モジュール

支出分類、FIRE計算、トレンド分析を統合して、
経済的自由に向けたプログレスと改善提案を提供します。
"""

from __future__ import annotations

from typing import Any

from household_mcp.analysis.expense_classifier import (
    ClassificationResult,
    ExpenseClassifier,
)
from household_mcp.analysis.fire_calculator import FIRECalculator
from household_mcp.analysis.trend_statistics import (
    ProjectionScenario,
    TrendStatistics,
)


class FinancialIndependenceAnalyzer:
    """
    経済的自由度分析クラス

    以下の分析を行う統合アナライザー：
    1. 定期/不定期支出の分類
    2. FIRE目標資産の計算
    3. 資産成長率の分析
    4. 達成シナリオの投影
    5. 改善提案の生成
    """

    def __init__(
        self, min_data_points: int = 3, projection_months: list[int] | None = None
    ):
        """
        初期化

        Args:
            min_data_points: 成長率分析に必要なデータポイント数
            projection_months: 投影対象月数（デフォルト: [12, 36, 60]）

        """
        self.min_data_points = min_data_points
        self.projection_months = projection_months or [12, 36, 60]

    def get_status(
        self,
        current_assets: float,
        target_assets: float,
        annual_expense: float,
        asset_history: list[float] | None = None,
    ) -> dict[str, Any]:
        """
        現在のFIREプログレスを取得

        Args:
            current_assets: 現在の資産額
            target_assets: 目標資産額（設定されている場合）
            annual_expense: 年支出額
            asset_history: 月次資産額の履歴（オプション）

        Returns:
            FIREプログレス情報を含む辞書

        """
        result = {
            "timestamp": None,
            "current_assets": current_assets,
            "target_assets": target_assets,
            "progress_rate": 0.0,
            "is_achieved": False,
            "fire_target": 0.0,
            "annual_expense": annual_expense,
            "growth_analysis": None,
            "months_to_fi": None,
        }

        # FIRE目標を計算
        fire_target = FIRECalculator.calculate_fire_target(annual_expense)
        result["fire_target"] = fire_target

        # 進捗率を計算
        progress_rate = FIRECalculator.calculate_progress_rate(
            current_assets, fire_target
        )
        result["progress_rate"] = progress_rate

        # 達成判定
        is_achieved = FIRECalculator.is_fi_achieved(current_assets, fire_target)
        result["is_achieved"] = is_achieved

        # 成長率分析
        if asset_history and len(asset_history) >= self.min_data_points:
            growth_analysis = TrendStatistics.calculate_monthly_growth_rate(
                asset_history, method="regression"
            )
            result["growth_analysis"] = {
                "monthly_growth_rate": growth_analysis.monthly_growth_rate,
                "growth_rate_decimal": growth_analysis.growth_rate_decimal,
                "annual_growth_rate": growth_analysis.annual_growth_rate,
                "confidence": growth_analysis.confidence,
                "data_points": growth_analysis.data_points,
                "r_squared": growth_analysis.r_squared,
            }

            # FIRE達成までの月数を計算
            months_to_fi = TrendStatistics.calculate_months_to_fi(
                current_assets, fire_target, growth_analysis.growth_rate_decimal
            )
            result["months_to_fi"] = months_to_fi

        return result

    def calculate_scenarios(
        self,
        current_assets: float,
        annual_expense: float,
        asset_history: list[float],
        custom_scenarios: dict[str, float] | None = None,
    ) -> list[ProjectionScenario]:
        """
        複数のシナリオを計算

        デフォルトシナリオ:
        - 悲観的: 成長率の-30%
        - 中立的: 実績の成長率
        - 楽観的: 成長率の+30%

        Args:
            current_assets: 現在の資産額
            annual_expense: 年支出額
            asset_history: 月次資産額の履歴
            custom_scenarios: カスタムシナリオ
                {"シナリオ名": 月間成長率（小数形式）, ...}

        Returns:
            複数のProjectionScenarioリスト

        """
        # FIRE目標を計算
        fire_target = FIRECalculator.calculate_fire_target(annual_expense)

        # 基本となる成長率を計算
        growth_analysis = TrendStatistics.calculate_monthly_growth_rate(
            asset_history, method="regression"
        )
        base_growth = growth_analysis.growth_rate_decimal

        # シナリオを作成
        scenarios: list[ProjectionScenario] = []

        # デフォルトシナリオ
        default_scenarios = {
            "悲観的": base_growth * 0.7,  # 基本成長率の70%
            "中立的": base_growth,
            "楽観的": base_growth * 1.3,  # 基本成長率の130%
        }

        # カスタムシナリオを統合
        all_scenarios = {**default_scenarios, **(custom_scenarios or {})}

        # 各シナリオを投影
        for name, growth_rate in all_scenarios.items():
            scenario = TrendStatistics.create_projection_scenario(
                name, current_assets, fire_target, growth_rate
            )
            scenarios.append(scenario)

        return scenarios

    def classify_expenses(
        self, category_history: dict[str, list[float]], months: int
    ) -> dict[str, ClassificationResult]:
        """
        支出カテゴリを定期/不定期に分類

        Args:
            category_history: カテゴリごとの月次支出額
                {"カテゴリ名": [月1, 月2, ...], ...}
            months: 分析対象月数

        Returns:
            分類結果の辞書
                {"カテゴリ名": ClassificationResult, ...}

        """
        results: dict[str, ClassificationResult] = {}

        for category_name, amounts in category_history.items():
            # ゼロを除いた実際の発生月をカウント
            non_zero_amounts = [a for a in amounts if a > 0]
            occurrences = len(non_zero_amounts)

            if occurrences == 0:
                # 発生なしのカテゴリ
                results[category_name] = ClassificationResult(
                    classification="irregular",
                    confidence=1.0,
                    reasoning={"reason": "発生なし"},
                )
            else:
                # 分類を実行
                classification = ExpenseClassifier.classify(
                    non_zero_amounts, months, occurrences
                )
                results[category_name] = classification

        return results

    def suggest_improvements(
        self,
        current_assets: float,
        annual_expense: float,
        asset_history: list[float],
        category_classification: dict[str, ClassificationResult],
    ) -> list[dict[str, Any]]:
        """
        改善提案を生成

        Args:
            current_assets: 現在の資産額
            annual_expense: 年支出額
            asset_history: 月次資産額の履歴
            category_classification: 支出分類結果

        Returns:
            改善提案リスト（優先度順）

        """
        suggestions: list[dict[str, Any]] = []

        # FIRE目標を計算
        fire_target = FIRECalculator.calculate_fire_target(annual_expense)

        # 現在の進捗率を計算
        progress_rate = FIRECalculator.calculate_progress_rate(
            current_assets, fire_target
        )

        # 成長率を分析
        if len(asset_history) >= self.min_data_points:
            growth_analysis = TrendStatistics.calculate_monthly_growth_rate(
                asset_history
            )

            # 提案1: 成長率が低い場合
            if growth_analysis.growth_rate_decimal < 0.01:  # 1%未満
                suggestions.append(
                    {
                        "priority": "HIGH",
                        "type": "growth_rate",
                        "title": "資産成長率の改善が必要です",
                        "description": (
                            f"月間成長率が{growth_analysis.monthly_growth_rate:.2f}%"
                            "と低い状況です。"
                            "収入増加または支出削減により、成長率を高める"
                            "ことをお勧めします。"
                        ),
                        "impact": "月間成長率が1%上昇すると、FIRE達成までの"
                        "期間が大幅に短縮されます",
                    }
                )

            # 提案2: 達成までの期間を計算
            months_to_fi = TrendStatistics.calculate_months_to_fi(
                current_assets, fire_target, growth_analysis.growth_rate_decimal
            )

            if months_to_fi and months_to_fi > 120:  # 10年以上
                suggestions.append(
                    {
                        "priority": "MEDIUM",
                        "type": "timeline",
                        "title": "FIRE達成までにかなりの期間が必要です",
                        "description": (
                            f"現在のペースでは、FIRE達成に約"
                            f"{months_to_fi:.0f}ヶ月（"
                            f"{months_to_fi/12:.1f}年）必要です。"
                        ),
                        "impact": "支出を10%削減できれば、達成期間は"
                        "約1年短縮されます",
                    }
                )

        # 提案3: 不定期支出の削減機会
        irregular_categories = [
            cat
            for cat, result in category_classification.items()
            if result.classification == "irregular"
        ]

        if irregular_categories:
            suggestions.append(
                {
                    "priority": "MEDIUM",
                    "type": "irregular_expense",
                    "title": "不定期支出の削減機会があります",
                    "description": (
                        f"以下のカテゴリが不定期支出に分類されました: "
                        f"{', '.join(irregular_categories[:3])}"
                        f"{'ほか' if len(irregular_categories) > 3 else ''}"
                    ),
                    "impact": "不定期支出の20%削減で、月間支出を" "平均1%削減できます",
                }
            )

        # 提案4: 進捗が遅い場合
        if progress_rate < 50:  # 50%未満
            suggestions.append(
                {
                    "priority": "HIGH",
                    "type": "progress",
                    "title": "FIRE達成まで道のりがあります",
                    "description": (
                        f"現在の進捗は{progress_rate:.1f}%です。"
                        "次のステップを検討してください: "
                        "1) 月間支出の見直し "
                        "2) 副収入の検討 "
                        "3) 投資リターンの最適化"
                    ),
                    "impact": "年間50万円の追加貯蓄で、約2年間の"
                    "達成期間短縮が見込めます",
                }
            )

        return suggestions
