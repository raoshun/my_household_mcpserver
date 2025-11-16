"""EnhancedFIRESimulator 単体テスト

TASK-2008: Phase 2 単体テスト
- 4種類のFIREタイプ計算テスト
- シナリオ比較テスト
- What-Ifシミュレーションテスト
- エッジケーステスト
"""

from datetime import date
from decimal import Decimal

import pytest

from household_mcp.analysis.enhanced_fire_simulator import (
    EnhancedFIRESimulator,
    FIREScenario,
    FIRESimulationResult,
    FIREType,
)


@pytest.fixture
def simulator():
    """EnhancedFIRESimulatorインスタンス"""
    return EnhancedFIRESimulator()


class TestFIRETargetCalculation:
    """FIRE目標資産額計算テスト"""

    def test_standard_fire_basic(self, simulator):
        """標準FIRE: 年間支出 × 25"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.STANDARD,
            annual_expense=Decimal("4000000"),
        )
        assert target == Decimal("100000000.00")

    def test_standard_fire_with_passive_income(self, simulator):
        """標準FIRE: 受動的収入考慮"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.STANDARD,
            annual_expense=Decimal("4000000"),
            passive_income=Decimal("1000000"),
        )
        # (4000000 - 1000000) × 25 = 75000000
        assert target == Decimal("75000000.00")

    def test_standard_fire_zero_expense(self, simulator):
        """標準FIRE: 支出ゼロは例外"""
        with pytest.raises(ValueError, match="年間支出は正の値"):
            simulator.calculate_fire_target(
                fire_type=FIREType.STANDARD,
                annual_expense=Decimal("0"),
            )

    def test_standard_fire_passive_covers_all(self, simulator):
        """標準FIRE: 受動的収入で全支出カバー"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.STANDARD,
            annual_expense=Decimal("3000000"),
            passive_income=Decimal("4000000"),
        )
        assert target == Decimal("0.00")


class TestCoastFIRE:
    """コーストFIREテスト"""

    def test_coast_fire_basic(self, simulator):
        """コーストFIRE: 基本計算"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.COAST,
            annual_expense=Decimal("4000000"),
            current_age=35,
            current_assets=Decimal("10000000"),
            annual_return_rate=Decimal("0.05"),
        )
        # 老後必要額: 4000000 × 25 = 100000000
        # 現資産の30年後: 10000000 × 1.05^30 ≈ 43219424
        # 必要追加: 100000000 - 43219424 ≈ 56780576
        assert target > Decimal("50000000")
        assert target < Decimal("60000000")

    def test_coast_fire_already_retired(self, simulator):
        """コーストFIRE: 既に老後年齢"""
        with pytest.raises(ValueError, match="既に老後年齢"):
            simulator.calculate_fire_target(
                fire_type=FIREType.COAST,
                annual_expense=Decimal("4000000"),
                current_age=70,
                current_assets=Decimal("10000000"),
            )

    def test_coast_fire_sufficient_assets(self, simulator):
        """コーストFIRE: 現資産で十分"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.COAST,
            annual_expense=Decimal("4000000"),
            current_age=35,
            current_assets=Decimal("50000000"),
            annual_return_rate=Decimal("0.07"),
        )
        # 50000000 × 1.07^30 ≈ 380612699 > 100000000
        assert target == Decimal("0.00")


class TestBaristaFIRE:
    """バリスタFIREテスト"""

    def test_barista_fire_basic(self, simulator):
        """バリスタFIRE: 基本計算"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.BARISTA,
            annual_expense=Decimal("4000000"),
            part_time_income=Decimal("2000000"),
        )
        # (4000000 - 2000000) × 25 = 50000000
        assert target == Decimal("50000000.00")

    def test_barista_fire_no_part_time_income(self, simulator):
        """バリスタFIRE: パートタイム収入なしは例外"""
        with pytest.raises(ValueError, match="パートタイム収入が必要"):
            simulator.calculate_fire_target(
                fire_type=FIREType.BARISTA,
                annual_expense=Decimal("4000000"),
            )

    def test_barista_fire_income_covers_all(self, simulator):
        """バリスタFIRE: パートタイム収入で全支出カバー"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.BARISTA,
            annual_expense=Decimal("3000000"),
            part_time_income=Decimal("4000000"),
        )
        assert target == Decimal("0.00")


class TestSideFIRE:
    """サイドFIREテスト"""

    def test_side_fire_basic(self, simulator):
        """サイドFIRE: 基本計算"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.SIDE,
            annual_expense=Decimal("4000000"),
            side_income=Decimal("1500000"),
        )
        # (4000000 - 1500000) × 25 = 62500000
        assert target == Decimal("62500000.00")

    def test_side_fire_no_side_income(self, simulator):
        """サイドFIRE: 副業収入なしは例外"""
        with pytest.raises(ValueError, match="副業収入が必要"):
            simulator.calculate_fire_target(
                fire_type=FIREType.SIDE,
                annual_expense=Decimal("4000000"),
            )

    def test_side_fire_income_covers_all(self, simulator):
        """サイドFIRE: 副業収入で全支出カバー"""
        target = simulator.calculate_fire_target(
            fire_type=FIREType.SIDE,
            annual_expense=Decimal("3000000"),
            side_income=Decimal("5000000"),
        )
        assert target == Decimal("0.00")


class TestScenarioSimulation:
    """シナリオシミュレーションテスト"""

    def test_simulate_scenario_basic(self, simulator):
        """基本的なシナリオシミュレーション"""
        scenario = FIREScenario(
            name="標準プラン",
            fire_type=FIREType.STANDARD,
            initial_assets=Decimal("5000000"),
            monthly_savings=Decimal("200000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0.02"),
            passive_income=Decimal("1600000"),  # 年間160万 → 月13.3万
        )

        result = simulator.simulate_scenario(scenario)

        assert result.scenario_name == "標準プラン"
        assert result.fire_type == FIREType.STANDARD
        assert result.months_to_fire > 0
        assert result.months_to_fire < 1200
        assert len(result.asset_timeline) > 0
        assert "リスク" in result.risk_assessment

    def test_simulate_scenario_high_savings(self, simulator):
        """高貯蓄シナリオ"""
        scenario = FIREScenario(
            name="高貯蓄プラン",
            fire_type=FIREType.STANDARD,
            initial_assets=Decimal("10000000"),
            monthly_savings=Decimal("500000"),
            annual_return_rate=Decimal("0.07"),
            inflation_rate=Decimal("0.02"),
            passive_income=Decimal("800000"),  # 年間80万
        )

        result = simulator.simulate_scenario(scenario)

        # passive_income * 25 = 20,000,000が目標
        # 高貯蓄（月50万）+ 高利回り(7%)なので早期達成見込み
        assert result.months_to_fire < 360  # 30年未満
        assert "リスク" in result.risk_assessment


class TestMultipleScenarios:
    """複数シナリオテスト"""

    def test_simulate_scenarios_multiple(self, simulator):
        """複数シナリオ一括シミュレーション"""
        scenarios = [
            FIREScenario(
                name="保守的",
                fire_type=FIREType.STANDARD,
                initial_assets=Decimal("5000000"),
                monthly_savings=Decimal("100000"),
                annual_return_rate=Decimal("0.03"),
                inflation_rate=Decimal("0.02"),
                passive_income=Decimal("1200000"),
            ),
            FIREScenario(
                name="標準",
                fire_type=FIREType.STANDARD,
                initial_assets=Decimal("5000000"),
                monthly_savings=Decimal("200000"),
                annual_return_rate=Decimal("0.05"),
                inflation_rate=Decimal("0.02"),
                passive_income=Decimal("1600000"),
            ),
            FIREScenario(
                name="積極的",
                fire_type=FIREType.STANDARD,
                initial_assets=Decimal("5000000"),
                monthly_savings=Decimal("300000"),
                annual_return_rate=Decimal("0.07"),
                inflation_rate=Decimal("0.02"),
                passive_income=Decimal("2000000"),
            ),
        ]

        results = simulator.simulate_scenarios(scenarios)

        assert len(results) == 3
        assert all(isinstance(r, FIRESimulationResult) for r in results)

        # 貯蓄額順に到達時間が短くなる
        assert results[2].months_to_fire < results[1].months_to_fire
        assert results[1].months_to_fire < results[0].months_to_fire

    def test_simulate_scenarios_max_limit(self, simulator):
        """シナリオ数上限テスト"""
        scenarios = [
            FIREScenario(
                name=f"シナリオ{i}",
                fire_type=FIREType.STANDARD,
                initial_assets=Decimal("5000000"),
                monthly_savings=Decimal("100000"),
                annual_return_rate=Decimal("0.05"),
                inflation_rate=Decimal("0.02"),
                passive_income=Decimal("1600000"),
            )
            for i in range(6)
        ]

        with pytest.raises(ValueError, match="シナリオは最大5件"):
            simulator.simulate_scenarios(scenarios)


class TestCompareScenarios:
    """シナリオ比較テスト"""

    def test_compare_scenarios_basic(self, simulator):
        """基本的なシナリオ比較"""
        scenarios = [
            FIREScenario(
                name="遅いプラン",
                fire_type=FIREType.STANDARD,
                initial_assets=Decimal("5000000"),
                monthly_savings=Decimal("100000"),
                annual_return_rate=Decimal("0.05"),
                inflation_rate=Decimal("0.02"),
                passive_income=Decimal("1200000"),
            ),
            FIREScenario(
                name="速いプラン",
                fire_type=FIREType.STANDARD,
                initial_assets=Decimal("10000000"),
                monthly_savings=Decimal("400000"),
                annual_return_rate=Decimal("0.07"),
                inflation_rate=Decimal("0.02"),
                passive_income=Decimal("2400000"),
            ),
        ]

        results = simulator.simulate_scenarios(scenarios)
        comparison = simulator.compare_scenarios(results)

        assert "fastest_scenario" in comparison
        assert "min_savings_scenario" in comparison
        assert "all_scenarios" in comparison
        assert comparison["fastest_scenario"]["name"] == "速いプラン"
        assert len(comparison["all_scenarios"]) == 2

    def test_compare_scenarios_empty(self, simulator):
        """空のシナリオ比較"""
        comparison = simulator.compare_scenarios([])
        assert "error" in comparison


class TestWhatIfSimulation:
    """What-Ifシミュレーションテスト"""

    def test_what_if_increase_savings(self, simulator):
        """貯蓄額増加のWhat-If"""
        base_scenario = FIREScenario(
            name="ベース",
            fire_type=FIREType.STANDARD,
            initial_assets=Decimal("5000000"),
            monthly_savings=Decimal("200000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0.02"),
            passive_income=Decimal("1600000"),
        )

        changes = {"monthly_savings": Decimal("300000")}
        result = simulator.what_if_simulation(base_scenario, changes)

        assert "base" in result
        assert "modified" in result
        assert "impact" in result
        assert result["impact"]["months_saved"] > 0

    def test_what_if_increase_return_rate(self, simulator):
        """運用利回り上昇のWhat-If"""
        base_scenario = FIREScenario(
            name="ベース",
            fire_type=FIREType.STANDARD,
            initial_assets=Decimal("5000000"),
            monthly_savings=Decimal("200000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0.02"),
            passive_income=Decimal("1600000"),
        )

        changes = {"annual_return_rate": Decimal("0.07")}
        result = simulator.what_if_simulation(base_scenario, changes)

        assert result["impact"]["months_saved"] > 0
        assert result["impact"]["improvement_pct"] > 0


class TestRiskAssessment:
    """リスク評価テスト"""

    def test_risk_assessment_short_term(self, simulator):
        """短期計画のリスク評価"""
        scenario = FIREScenario(
            name="短期プラン",
            fire_type=FIREType.STANDARD,
            initial_assets=Decimal("30000000"),
            monthly_savings=Decimal("500000"),
            annual_return_rate=Decimal("0.07"),
            inflation_rate=Decimal("0.02"),
            passive_income=Decimal("3200000"),
        )

        result = simulator.simulate_scenario(scenario)

        # 10年以内 → 最低リスク
        if result.months_to_fire <= 120:
            assert "最低リスク" in result.risk_assessment

    def test_risk_assessment_long_term(self, simulator):
        """長期計画のリスク評価"""
        scenario = FIREScenario(
            name="長期プラン",
            fire_type=FIREType.STANDARD,
            initial_assets=Decimal("1000000"),
            monthly_savings=Decimal("50000"),
            annual_return_rate=Decimal("0.03"),
            inflation_rate=Decimal("0.02"),
            passive_income=Decimal("800000"),
        )

        result = simulator.simulate_scenario(scenario)

        # 30年超 → 高リスク
        if result.months_to_fire > 360:
            assert "高リスク" in result.risk_assessment


class TestDataclassConversion:
    """データクラス変換テスト"""

    def test_fire_simulation_result_to_dict(self, simulator):
        """FIRESimulationResult辞書変換"""
        scenario = FIREScenario(
            name="テスト",
            fire_type=FIREType.STANDARD,
            initial_assets=Decimal("5000000"),
            monthly_savings=Decimal("200000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0.02"),
            passive_income=Decimal("1600000"),
        )

        result = simulator.simulate_scenario(scenario)
        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["scenario_name"] == "テスト"
        assert result_dict["fire_type"] == FIREType.STANDARD.value
        assert isinstance(result_dict["target_assets"], float)
        assert isinstance(result_dict["months_to_fire"], int)
        assert isinstance(result_dict["achievement_date"], str)
