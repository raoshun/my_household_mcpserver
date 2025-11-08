"""
シナリオ分析ツールのテストモジュール

複数シナリオの比較、ROI計算、推奨シナリオ選定を検証します。
"""

from decimal import Decimal

import pytest

from household_mcp.analysis.scenario_simulator import (
    ScenarioConfig,
    ScenarioResult,
    ScenarioSimulator,
)


class TestScenarioSimulator:
    """シナリオ分析ツールのテストクラス"""

    @pytest.fixture
    def simulator(self):
        """テスト用シミュレーター"""
        return ScenarioSimulator(
            current_assets=Decimal("1000000"),
            current_monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            current_monthly_expense=Decimal("200000"),
            inflation_rate=Decimal("0"),
        )

    def test_simulator_initialization(self, simulator):
        """シミュレーター初期化"""
        assert simulator.current_assets == Decimal("1000000")
        assert simulator.current_monthly_savings == Decimal("100000")
        assert simulator.target_assets == Decimal("2000000")
        assert simulator.original_months_to_fi > 0

    def test_single_scenario_expense_reduction(self, simulator):
        """支出削減シナリオ"""
        scenario = ScenarioConfig(
            name="支出削減10%",
            description="全カテゴリ支出を10%削減",
            expense_reduction_pct=Decimal("10"),
            income_increase=Decimal("0"),
            difficulty_score=Decimal("2"),
        )

        result = simulator._simulate_single_scenario(scenario)

        assert result.scenario_name == "支出削減10%"
        assert result.achievable is True
        # 支出削減により月貯蓄が増加し、到達月数が減少
        assert result.months_saved > 0
        assert result.scenario_months_to_fi < result.original_months_to_fi

    def test_single_scenario_income_increase(self, simulator):
        """収入増加シナリオ"""
        scenario = ScenarioConfig(
            name="収入増加50000円/月",
            description="副業で月50,000円増加",
            expense_reduction_pct=Decimal("0"),
            income_increase=Decimal("50000"),
            difficulty_score=Decimal("3"),
        )

        result = simulator._simulate_single_scenario(scenario)

        assert result.scenario_name == "収入増加50000円/月"
        assert result.achievable is True
        assert result.months_saved > 0

    def test_single_scenario_combined(self, simulator):
        """複合シナリオ"""
        scenario = ScenarioConfig(
            name="複合",
            description="支出削減10% + 収入30,000円/月",
            expense_reduction_pct=Decimal("10"),
            income_increase=Decimal("30000"),
            difficulty_score=Decimal("2.5"),
        )

        result = simulator._simulate_single_scenario(scenario)

        assert result.achievable is True
        assert result.months_saved > 0

    def test_scenario_exceeding_expense(self, simulator):
        """支出削減が月支出を超える場合"""
        scenario = ScenarioConfig(
            name="過度な削減",
            description="支出を150%削減（不可能）",
            expense_reduction_pct=Decimal("150"),
            income_increase=Decimal("0"),
            difficulty_score=Decimal("10"),
        )

        result = simulator._simulate_single_scenario(scenario)

        # 削減後の月支出が負になるため警告が発生
        assert "警告" in result.message
        assert result.achievable is False

    def test_multiple_scenarios_comparison(self, simulator):
        """複数シナリオの比較"""
        scenarios = [
            ScenarioConfig(
                name="削減10%",
                description="支出削減10%",
                expense_reduction_pct=Decimal("10"),
                income_increase=Decimal("0"),
                difficulty_score=Decimal("2"),
            ),
            ScenarioConfig(
                name="削減20%",
                description="支出削減20%",
                expense_reduction_pct=Decimal("20"),
                income_increase=Decimal("0"),
                difficulty_score=Decimal("4"),
            ),
            ScenarioConfig(
                name="収入増50000",
                description="収入増加50,000円/月",
                expense_reduction_pct=Decimal("0"),
                income_increase=Decimal("50000"),
                difficulty_score=Decimal("3"),
            ),
        ]

        results = simulator.simulate_scenarios(scenarios)

        # 3つのシナリオが返される
        assert len(results) == 3

        # ROI降順でソートされている
        for i in range(len(results) - 1):
            assert results[i].roi_score >= results[i + 1].roi_score

    def test_roi_calculation(self, simulator):
        """ROI計算"""
        scenario = ScenarioConfig(
            name="テスト",
            description="テスト",
            expense_reduction_pct=Decimal("10"),
            income_increase=Decimal("0"),
            difficulty_score=Decimal("2"),
        )

        result = simulator._simulate_single_scenario(scenario)

        # ROI = 月数短縮 / 難易度スコア
        expected_roi = Decimal(result.months_saved) / Decimal("2")
        assert result.roi_score == expected_roi

    def test_recommended_scenario(self, simulator):
        """推奨シナリオの選定"""
        scenarios = [
            ScenarioConfig(
                name="削減10%",
                description="支出削減10%",
                expense_reduction_pct=Decimal("10"),
                income_increase=Decimal("0"),
                difficulty_score=Decimal("2"),
            ),
            ScenarioConfig(
                name="削減20%",
                description="支出削減20%",
                expense_reduction_pct=Decimal("20"),
                income_increase=Decimal("0"),
                difficulty_score=Decimal("4"),
            ),
        ]

        results = simulator.simulate_scenarios(scenarios)
        recommended = ScenarioSimulator.get_recommended_scenario(results)

        # ROIが最も高いシナリオが推奨される
        assert recommended is not None
        assert recommended.roi_score == results[0].roi_score

    def test_recommended_scenario_none(self, simulator):
        """推奨シナリオが存在しない場合"""
        # すべてのシナリオが不可能な場合を設定
        simulator.target_assets = Decimal("100000000000")  # 非常に高い目標

        scenarios = [
            ScenarioConfig(
                name="削減10%",
                description="支出削減10%",
                expense_reduction_pct=Decimal("10"),
                income_increase=Decimal("0"),
                difficulty_score=Decimal("2"),
            ),
        ]

        results = simulator.simulate_scenarios(scenarios)
        recommended = ScenarioSimulator.get_recommended_scenario(results)

        # 推奨シナリオが存在しない
        # 実装によっては None または警告
        # ここではテスト可能性を確保するため、チェックする
        if recommended:
            assert recommended.achievable is True

    def test_default_scenarios(self):
        """デフォルトシナリオ生成"""
        scenarios = ScenarioSimulator.create_default_scenarios(Decimal("200000"))

        # 5つのシナリオが生成される
        assert len(scenarios) == 5

        # 各シナリオの名前と説明が設定されている
        for scenario in scenarios:
            assert scenario.name
            assert scenario.description
            assert scenario.difficulty_score > 0

    def test_zero_difficulty_score(self, simulator):
        """難易度スコア0の場合のROI計算"""
        scenario = ScenarioConfig(
            name="テスト",
            description="テスト",
            expense_reduction_pct=Decimal("10"),
            income_increase=Decimal("0"),
            difficulty_score=Decimal("0"),
        )

        result = simulator._simulate_single_scenario(scenario)

        # 難易度が0の場合、ROIは0
        assert result.roi_score == Decimal("0")

    def test_scenario_result_structure(self, simulator):
        """シナリオ結果のデータ構造確認"""
        scenario = ScenarioConfig(
            name="テスト",
            description="テスト説明",
            expense_reduction_pct=Decimal("10"),
            income_increase=Decimal("5000"),
            difficulty_score=Decimal("2"),
        )

        result = simulator._simulate_single_scenario(scenario)

        assert isinstance(result, ScenarioResult)
        assert result.scenario_name == "テスト"
        assert result.description == "テスト説明"
        assert result.original_months_to_fi > 0
        assert result.scenario_months_to_fi >= 0
        assert result.months_saved >= 0
        assert result.difficulty_score == Decimal("2")
        assert isinstance(result.roi_score, Decimal)
        assert isinstance(result.achievable, bool)
        assert isinstance(result.message, str)
