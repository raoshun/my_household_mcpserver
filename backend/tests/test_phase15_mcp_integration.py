"""
Phase 15 分析ツール統合テスト

新しい3つの分析ツール（FIRE計算、シナリオ分析、パターン分析）の
統合動作を検証します。
"""


class TestPhase15AnalysisIntegration:
    """Phase 15分析ツール統合テスト"""

    def test_fire_calculator_integration(self):
        """FIRE計算エンジン統合"""
        from decimal import Decimal

        from household_mcp.analysis.fire_calculator import calculate_fire_index

        result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0.0"),
        )

        assert result.feasible is True
        assert result.months_to_fi > 0
        assert len(result.achieved_assets_timeline) > 0
        assert len(result.scenarios) == 3

    def test_scenario_simulator_integration(self):
        """シナリオシミュレーター統合"""
        from decimal import Decimal

        from household_mcp.analysis.scenario_simulator import ScenarioSimulator

        simulator = ScenarioSimulator(
            current_assets=Decimal("1000000"),
            current_monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            current_monthly_expense=Decimal("200000"),
        )

        scenarios = ScenarioSimulator.create_default_scenarios(Decimal("200000"))
        results = simulator.simulate_scenarios(scenarios)

        assert len(results) == 5
        assert results[0].roi_score >= results[-1].roi_score

    def test_pattern_analyzer_integration(self):
        """パターン分析エンジン統合"""
        from decimal import Decimal

        from household_mcp.analysis.expense_pattern_analyzer import (
            ExpensePatternAnalyzer,
        )

        analyzer = ExpensePatternAnalyzer()

        expense_data = {
            "食費": [
                Decimal("30000"),
                Decimal("32000"),
                Decimal("28000"),
                Decimal("35000"),
                Decimal("29000"),
                Decimal("31000"),
                Decimal("33000"),
                Decimal("27000"),
                Decimal("36000"),
                Decimal("29000"),
                Decimal("32000"),
                Decimal("31000"),
            ]
        }

        result = analyzer.analyze_expenses(expense_data)

        assert len(result.classifications) > 0
        assert len(result.seasonality) > 0
        assert len(result.trends) > 0

    def test_fire_calculation_performance(self):
        """FIRE計算パフォーマンス（< 100ms）"""
        import time
        from decimal import Decimal

        from household_mcp.analysis.fire_calculator import calculate_fire_index

        start = time.time()
        result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
        )
        elapsed = time.time() - start

        assert elapsed < 0.1  # 100ms以内
        assert result.feasible is True

    def test_scenario_simulation_performance(self):
        """シナリオシミュレーターパフォーマンス（< 500ms）"""
        import time
        from decimal import Decimal

        from household_mcp.analysis.scenario_simulator import ScenarioSimulator

        start = time.time()
        simulator = ScenarioSimulator(
            current_assets=Decimal("1000000"),
            current_monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            current_monthly_expense=Decimal("200000"),
        )
        scenarios = ScenarioSimulator.create_default_scenarios(Decimal("200000"))
        results = simulator.simulate_scenarios(scenarios)
        elapsed = time.time() - start

        assert elapsed < 0.5  # 500ms以内
        assert len(results) > 0

    def test_full_workflow_integration(self):
        """フルワークフロー統合テスト"""
        from decimal import Decimal

        from household_mcp.analysis.fire_calculator import calculate_fire_index
        from household_mcp.analysis.scenario_simulator import ScenarioSimulator

        # Step 1: FIRE計算
        fire_result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
        )

        assert fire_result.feasible is True
        original_months = fire_result.months_to_fi

        # Step 2: シナリオ分析で改善施策を評価
        simulator = ScenarioSimulator(
            current_assets=Decimal("1000000"),
            current_monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            current_monthly_expense=Decimal("200000"),
        )

        scenarios = ScenarioSimulator.create_default_scenarios(Decimal("200000"))
        results = simulator.simulate_scenarios(scenarios)
        recommended = ScenarioSimulator.get_recommended_scenario(results)

        # Step 3: 検証
        assert simulator.original_months_to_fi == original_months
        assert recommended is not None
        assert recommended.achievable is True
        assert recommended.months_saved > 0
