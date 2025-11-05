"""
FIRE分析モジュール用ユニットテスト

火災分析クラスのテスト
"""

from __future__ import annotations

import pytest

from household_mcp.analysis.expense_classifier import (
    ClassificationResult,
    ExpenseClassifier,
)
from household_mcp.analysis.financial_independence import FinancialIndependenceAnalyzer
from household_mcp.analysis.fire_calculator import FIRECalculator
from household_mcp.analysis.trend_statistics import TrendStatistics


class TestFIRECalculator:
    """FIRECalculatorのテスト"""

    def test_calculate_fire_target_basic(self):
        """基本的なFIRE目標計算"""
        result = FIRECalculator.calculate_fire_target(1000000)
        assert result == 25000000

    def test_calculate_fire_target_custom_multiplier(self):
        """カスタム倍率でのFIRE目標計算"""
        result = FIRECalculator.calculate_fire_target(1000000, custom_multiplier=30)
        assert result == 30000000

    def test_calculate_fire_target_invalid_expense(self):
        """無効な支出額の処理"""
        with pytest.raises(ValueError):
            FIRECalculator.calculate_fire_target(0)

        with pytest.raises(ValueError):
            FIRECalculator.calculate_fire_target(-100000)

    def test_calculate_fire_target_invalid_multiplier(self):
        """無効な倍率の処理"""
        with pytest.raises(ValueError):
            FIRECalculator.calculate_fire_target(1000000, custom_multiplier=0)

        with pytest.raises(ValueError):
            FIRECalculator.calculate_fire_target(1000000, custom_multiplier=-5)

    def test_calculate_progress_rate(self):
        """進捗率の計算"""
        result = FIRECalculator.calculate_progress_rate(10000000, 25000000)
        assert result == 40.0

    def test_calculate_progress_rate_over_100(self):
        """目標超過時の進捗率"""
        result = FIRECalculator.calculate_progress_rate(30000000, 25000000)
        assert result == 120.0

    def test_is_fi_achieved_true(self):
        """FI達成判定（達成時）"""
        result = FIRECalculator.is_fi_achieved(25000000, 25000000)
        assert result is True

    def test_is_fi_achieved_false(self):
        """FI達成判定（未達成時）"""
        result = FIRECalculator.is_fi_achieved(10000000, 25000000)
        assert result is False


class TestExpenseClassifier:
    """ExpenseClassifierのテスト"""

    def test_classify_by_iqr_basic(self):
        """IQR法による分類（基本ケース）"""
        amounts = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190]
        result = ExpenseClassifier.classify_by_iqr(amounts)

        assert "has_outliers" in result
        assert "outlier_count" in result
        assert result["outlier_ratio"] >= 0

    def test_classify_by_iqr_with_outliers(self):
        """IQR法による分類（異常値あり）"""
        amounts = [100, 110, 120, 130, 140, 150, 160, 170, 180, 1000]
        result = ExpenseClassifier.classify_by_iqr(amounts, threshold=1.5)

        assert result["has_outliers"] is True
        assert result["outlier_count"] >= 1

    def test_classify_by_iqr_insufficient_data(self):
        """IQR法による分類（データ不足）"""
        amounts = [100, 110, 120]
        result = ExpenseClassifier.classify_by_iqr(amounts)

        assert result["has_outliers"] is False
        assert result["outlier_count"] == 0

    def test_classify_by_occurrence_regular(self):
        """発生頻度による分類（定期的）"""
        result = ExpenseClassifier.classify_by_occurrence(months=12, occurrences=10)

        assert result["is_regular"] is True
        threshold = ExpenseClassifier.OCCURRENCE_RATE_THRESHOLD
        assert result["occurrence_rate"] > threshold

    def test_classify_by_occurrence_irregular(self):
        """発生頻度による分類（不定期的）"""
        result = ExpenseClassifier.classify_by_occurrence(months=12, occurrences=5)

        assert result["is_regular"] is False
        threshold = ExpenseClassifier.OCCURRENCE_RATE_THRESHOLD
        assert result["occurrence_rate"] < threshold

    def test_classify_by_cv_stable(self):
        """変動係数による分類（安定的）"""
        amounts = [1000, 1010, 990, 1005, 995, 1000, 1020, 980]
        result = ExpenseClassifier.classify_by_cv(amounts)

        assert result["is_stable"] is True
        assert result["cv"] <= ExpenseClassifier.CV_THRESHOLD

    def test_classify_by_cv_variable(self):
        """変動係数による分類（変動的）"""
        amounts = [100, 500, 200, 800, 150, 900, 300, 1000]
        result = ExpenseClassifier.classify_by_cv(amounts)

        assert result["cv"] > 0.3

    def test_calculate_confidence(self):
        """信頼度の計算"""
        iqr_result = {"has_outliers": False, "outlier_ratio": 0.0}
        occurrence_result = {"is_regular": True, "occurrence_rate": 0.9}
        cv_result = {"is_stable": True, "cv": 0.2}

        confidence = ExpenseClassifier.calculate_confidence(
            iqr_result, occurrence_result, cv_result
        )

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8  # 高い信頼度

    def test_classify_complete(self):
        """完全な分類処理"""
        amounts = [10000, 10500, 9800, 10200, 9900, 10100]
        result = ExpenseClassifier.classify(amounts=amounts, months=12, occurrences=6)

        assert isinstance(result, ClassificationResult)
        assert result.classification in ["regular", "irregular"]
        assert 0.0 <= result.confidence <= 1.0

    def test_classify_no_occurrences(self):
        """発生なしの分類"""
        result = ExpenseClassifier.classify(amounts=[], months=12, occurrences=0)

        assert result.classification == "irregular"
        assert result.confidence == 1.0


class TestTrendStatistics:
    """TrendStatisticsのテスト"""

    def test_calculate_monthly_growth_rate_regression(self):
        """月次成長率の計算（回帰分析）"""
        asset_values = [1000000, 1050000, 1100000, 1150000, 1200000]
        result = TrendStatistics.calculate_monthly_growth_rate(
            asset_values, method="regression"
        )

        assert result.monthly_growth_rate > 0
        assert result.annual_growth_rate > 0
        assert 0.0 <= result.confidence <= 1.0

    def test_calculate_monthly_growth_rate_average(self):
        """月次成長率の計算（平均法）"""
        asset_values = [1000000, 1050000, 1100000, 1150000, 1200000]
        result = TrendStatistics.calculate_monthly_growth_rate(
            asset_values, method="average"
        )

        assert result.monthly_growth_rate > 0
        assert result.data_points >= 1

    def test_calculate_monthly_growth_rate_insufficient_data(self):
        """月次成長率の計算（データ不足）"""
        asset_values = [1000000, 1050000]

        with pytest.raises(ValueError):
            TrendStatistics.calculate_monthly_growth_rate(asset_values)

    def test_calculate_months_to_fi_achievable(self):
        """FIRE達成月数の計算（達成可能）"""
        months = TrendStatistics.calculate_months_to_fi(
            current_assets=5000000,
            target_assets=25000000,
            monthly_growth_rate=0.02,
        )

        assert months is not None
        assert months > 0

    def test_calculate_months_to_fi_already_achieved(self):
        """FIRE達成月数の計算（既に達成）"""
        months = TrendStatistics.calculate_months_to_fi(
            current_assets=30000000,
            target_assets=25000000,
            monthly_growth_rate=0.01,
        )

        assert months == 0.0

    def test_calculate_months_to_fi_unachievable(self):
        """FIRE達成月数の計算（達成不可能）"""
        months = TrendStatistics.calculate_months_to_fi(
            current_assets=5000000,
            target_assets=25000000,
            monthly_growth_rate=-0.01,
        )

        assert months is None

    def test_project_assets(self):
        """資産投影"""
        projected = TrendStatistics.project_assets(
            current_assets=1000000,
            monthly_growth_rate=0.01,
            months=12,
        )

        expected = 1000000 * ((1.01) ** 12)
        assert abs(projected - expected) < 100

    def test_create_projection_scenario(self):
        """投影シナリオの作成"""
        scenario = TrendStatistics.create_projection_scenario(
            scenario_name="中立的",
            current_assets=5000000,
            target_assets=25000000,
            monthly_growth_rate=0.01,
        )

        assert scenario.scenario_name == "中立的"
        assert scenario.current_assets == 5000000
        assert scenario.target_assets == 25000000
        assert scenario.is_achievable is True

    def test_calculate_moving_average(self):
        """移動平均の計算"""
        values = [100, 110, 120, 130, 140]
        ma = TrendStatistics.calculate_moving_average(values, window=3)

        assert len(ma) == len(values)
        assert ma[0] == 100  # 最初の値
        # 3ヶ月移動平均
        assert abs(ma[2] - 110.0) < 1  # (100+110+120)/3


class TestFinancialIndependenceAnalyzer:
    """FinancialIndependenceAnalyzerのテスト"""

    def test_get_status_basic(self):
        """FIREプログレス状態取得（基本）"""
        analyzer = FinancialIndependenceAnalyzer()
        result = analyzer.get_status(
            current_assets=5000000,
            target_assets=25000000,
            annual_expense=1000000,
        )

        assert "progress_rate" in result
        assert "fire_target" in result
        assert "is_achieved" in result
        assert result["fire_target"] == 25000000

    def test_get_status_with_growth_analysis(self):
        """FIREプログレス状態取得（成長率分析付き）"""
        analyzer = FinancialIndependenceAnalyzer()
        asset_history = [
            5000000,
            5100000,
            5200000,
            5310000,
            5420000,
            5540000,
        ]
        result = analyzer.get_status(
            current_assets=5540000,
            target_assets=25000000,
            annual_expense=1000000,
            asset_history=asset_history,
        )

        assert result["growth_analysis"] is not None
        assert result["months_to_fi"] is not None

    def test_calculate_scenarios(self):
        """複数シナリオの計算"""
        analyzer = FinancialIndependenceAnalyzer()
        asset_history = [
            5000000,
            5100000,
            5200000,
            5310000,
            5420000,
            5540000,
        ]
        scenarios = analyzer.calculate_scenarios(
            current_assets=5540000,
            annual_expense=1000000,
            asset_history=asset_history,
        )

        assert len(scenarios) >= 3  # 最小3つのシナリオ
        for scenario in scenarios:
            assert scenario.scenario_name in ["悲観的", "中立的", "楽観的"]

    def test_calculate_scenarios_with_custom(self):
        """カスタムシナリオを含める"""
        analyzer = FinancialIndependenceAnalyzer()
        asset_history = [
            5000000,
            5100000,
            5200000,
            5310000,
            5420000,
            5540000,
        ]
        custom_scenarios = {"アグレッシブ": 0.03}
        scenarios = analyzer.calculate_scenarios(
            current_assets=5540000,
            annual_expense=1000000,
            asset_history=asset_history,
            custom_scenarios=custom_scenarios,
        )

        assert len(scenarios) > 3

    def test_classify_expenses(self):
        """支出分類"""
        analyzer = FinancialIndependenceAnalyzer()
        category_history = {
            "食費": [50000, 52000, 48000, 51000, 49000, 50000],
            "交通費": [5000, 0, 5000, 0, 5000, 0],
            "医療費": [0, 0, 200000, 0, 0, 0],
        }
        result = analyzer.classify_expenses(category_history, months=6)

        assert "食費" in result
        assert "交通費" in result
        assert "医療費" in result

    def test_suggest_improvements(self):
        """改善提案の生成"""
        analyzer = FinancialIndependenceAnalyzer()
        asset_history = [
            1000000,
            1010000,
            1020000,
            1030000,
            1040000,
            1050000,
        ]
        category_classification = {
            "食費": ClassificationResult("regular", 0.8, {"reason": "定期的"}),
            "医療費": ClassificationResult("irregular", 0.6, {"reason": "不定期的"}),
        }
        suggestions = analyzer.suggest_improvements(
            current_assets=1050000,
            annual_expense=500000,
            asset_history=asset_history,
            category_classification=category_classification,
        )

        assert isinstance(suggestions, list)
        # 各提案に優先度とタイプがあることを確認
        for suggestion in suggestions:
            assert "priority" in suggestion
            assert "type" in suggestion


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
