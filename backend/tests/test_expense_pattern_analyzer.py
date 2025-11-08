"""
支出パターン分析ツールのテストモジュール

定期/変動/異常支出分類、季節性検出、トレンド分析を検証します。
"""

from decimal import Decimal

import pytest

from household_mcp.analysis.expense_pattern_analyzer import (
    ExpensePatternAnalyzer,
    ExpensePatternResult,
)


class TestExpensePatternAnalyzer:
    """支出パターン分析ツールのテストクラス"""

    @pytest.fixture
    def analyzer(self):
        """テスト用アナライザー"""
        return ExpensePatternAnalyzer()

    def test_analyzer_initialization(self, analyzer):
        """アナライザー初期化"""
        assert analyzer is not None
        assert analyzer.MIN_DATA_POINTS == 3

    def test_classify_regular_expense(self, analyzer):
        """定期支出の分類"""
        expense_data = {
            "家賃": [
                Decimal("100000"),
                Decimal("100000"),
                Decimal("100000"),
                Decimal("100000"),
                Decimal("100000"),
            ]
        }

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.classifications) == 1
        classification = result.classifications[0]
        assert classification.category == "家賃"
        assert classification.classification == "regular"
        assert classification.variance < Decimal("5")

    def test_classify_variable_expense(self, analyzer):
        """変動支出の分類"""
        expense_data = {
            "食費": [
                Decimal("30000"),
                Decimal("35000"),
                Decimal("28000"),
                Decimal("42000"),
                Decimal("31000"),
            ]
        }

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.classifications) == 1
        classification = result.classifications[0]
        assert classification.category == "食費"
        assert classification.classification == "variable"
        assert classification.variance >= Decimal("5")

    def test_classification_with_insufficient_data(self, analyzer):
        """データ不足でのスキップ"""
        expense_data = {"その他": [Decimal("10000"), Decimal("15000")]}  # 2データのみ

        result = analyzer.analyze_expenses(expense_data)

        # データ不足のため分類されない
        assert len(result.classifications) == 0

    def test_seasonality_detection_12_months(self, analyzer):
        """季節性検出（12ヶ月データ）"""
        # 12月に支出が増加するパターン
        expense_data = {
            "生活用品": [
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("25000"),  # 12月のみ増加
            ]
        }

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.seasonality) == 1
        seasonality = result.seasonality[0]
        assert seasonality.category == "生活用品"
        assert seasonality.has_seasonality is True
        assert seasonality.peak_month == 12
        assert seasonality.trough_month != 12

    def test_seasonality_detection_no_seasonality(self, analyzer):
        """季節性なしの検出"""
        expense_data = {"食費": [Decimal("20000")] * 12}

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.seasonality) == 1
        seasonality = result.seasonality[0]
        assert seasonality.has_seasonality is False

    def test_trend_analysis_increasing(self, analyzer):
        """増加トレンドの検出"""
        expense_data = {
            "交通費": [
                Decimal("5000"),
                Decimal("5500"),
                Decimal("6000"),
                Decimal("6500"),
                Decimal("7000"),
            ]
        }

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.category == "交通費"
        assert trend.trend_direction == "increasing"
        assert trend.slope > 0

    def test_trend_analysis_decreasing(self, analyzer):
        """減少トレンドの検出"""
        expense_data = {
            "通信費": [
                Decimal("10000"),
                Decimal("9500"),
                Decimal("9000"),
                Decimal("8500"),
                Decimal("8000"),
            ]
        }

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.category == "通信費"
        assert trend.trend_direction == "decreasing"
        assert trend.slope < 0

    def test_trend_analysis_flat(self, analyzer):
        """フラットトレンドの検出"""
        expense_data = {"保険料": [Decimal("5000")] * 5}

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.trends) == 1
        trend = result.trends[0]
        assert trend.category == "保険料"
        assert trend.trend_direction == "flat"
        assert abs(trend.slope) < 0.5

    def test_anomaly_detection(self, analyzer):
        """異常値検出"""
        expense_data = {
            "医療費": [
                Decimal("5000"),
                Decimal("5000"),
                Decimal("5000"),
                Decimal("50000"),  # 異常値
                Decimal("5000"),
            ]
        }

        anomalies = ExpensePatternAnalyzer.detect_anomalies(
            expense_data,
            sigma_threshold=1.0,  # 1σを使用
        )

        assert "医療費" in anomalies
        assert 3 in anomalies["医療費"]

    def test_anomaly_detection_insufficient_data(self, analyzer):
        """異常検出時のデータ不足チェック"""
        expense_data = {"その他": [Decimal("10000"), Decimal("15000")]}

        anomalies = ExpensePatternAnalyzer.detect_anomalies(expense_data)

        # データ不足のため異常検出されない
        assert "その他" not in anomalies

    def test_full_analysis_multiple_categories(self, analyzer):
        """複数カテゴリの分析"""
        expense_data = {
            "食費": [
                Decimal("30000"),
                Decimal("32000"),
                Decimal("28000"),
                Decimal("35000"),
                Decimal("29000"),
            ],
            "家賃": [Decimal("100000")] * 5,
            "交通費": [
                Decimal("5000"),
                Decimal("5500"),
                Decimal("6000"),
                Decimal("6500"),
                Decimal("7000"),
            ],
        }

        result = analyzer.analyze_expenses(expense_data)

        assert isinstance(result, ExpensePatternResult)
        assert len(result.classifications) == 3
        assert len(result.trends) == 3

    def test_result_structure(self, analyzer):
        """結果のデータ構造確認"""
        expense_data = {"食費": [Decimal("30000")] * 12}

        result = analyzer.analyze_expenses(expense_data)

        assert isinstance(result, ExpensePatternResult)
        assert hasattr(result, "classifications")
        assert hasattr(result, "seasonality")
        assert hasattr(result, "trends")
        assert hasattr(result, "analysis_period_months")
        assert result.analysis_period_months == 12

    def test_monthly_indices_average_100(self, analyzer):
        """月別指数の平均が100であることの確認"""
        expense_data = {
            "支出": [
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("15000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
                Decimal("10000"),
            ]
        }

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.seasonality) == 1
        seasonality = result.seasonality[0]
        # 月別指数の平均は100に近い（丸め誤差を考慮）
        avg_index = sum(seasonality.monthly_indices.values()) / 12
        assert abs(avg_index - 100) < 1
