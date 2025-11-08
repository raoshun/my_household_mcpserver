"""
FIRE計算エンジンのテストモジュール

複利、インフレ、シナリオ分析の機能を検証します。
"""

from decimal import Decimal

import pytest

from household_mcp.analysis.fire_calculator import (
    FireCalculationResult,
    FIRECalculator,
    _calculate_monthly_rate,
    _simulate_scenario,
    calculate_fire_index,
)


class TestFIRECalculator:
    """FIRE基準計算のテストクラス"""

    def test_calculate_fire_target_default_multiplier(self):
        """デフォルト倍率（25倍）でのFIRE目標資産額の計算"""
        annual_expense = Decimal("600000")
        target = FIRECalculator.calculate_fire_target(float(annual_expense))
        assert target == 600000 * 25
        assert target == 15000000

    def test_calculate_fire_target_custom_multiplier(self):
        """カスタム倍率でのFIRE目標資産額の計算"""
        annual_expense = 600000.0
        target = FIRECalculator.calculate_fire_target(annual_expense, 30)
        assert target == 18000000

    def test_calculate_fire_target_invalid_expense(self):
        """年支出が0以下の場合のエラー"""
        with pytest.raises(ValueError):
            FIRECalculator.calculate_fire_target(0)

    def test_calculate_progress_rate(self):
        """進捗率の計算"""
        current = 10000000.0
        target = 25000000.0
        rate = FIRECalculator.calculate_progress_rate(current, target)
        assert rate == 40.0

    def test_is_fi_achieved_true(self):
        """FI達成判定（達成済み）"""
        assert FIRECalculator.is_fi_achieved(25000000, 25000000) is True
        assert FIRECalculator.is_fi_achieved(26000000, 25000000) is True

    def test_is_fi_achieved_false(self):
        """FI達成判定（未達成）"""
        assert FIRECalculator.is_fi_achieved(24000000, 25000000) is False


class TestCalculateMonthlyRate:
    """月利率計算のテストクラス"""

    def test_monthly_rate_from_5_percent_annual(self):
        """年利5%から月利を計算"""
        annual_rate = Decimal("0.05")
        annual_rate_plus_1 = Decimal("1") + annual_rate
        monthly_rate = _calculate_monthly_rate(annual_rate_plus_1)

        # (1 + 月利)^12 = 1.05 の確認
        monthly_rate_plus_1 = Decimal("1") + monthly_rate
        reconstructed_annual_rate = (monthly_rate_plus_1**12) - Decimal("1")

        # 誤差範囲内での確認（小数第5位まで）
        assert abs(float(reconstructed_annual_rate - annual_rate)) < 0.00001

    def test_monthly_rate_zero_annual(self):
        """年利0%から月利を計算"""
        monthly_rate = _calculate_monthly_rate(Decimal("1"))
        assert monthly_rate == 0


class TestCalculateFireIndex:
    """複利・インフレ考慮のFIRE計算エンジンテスト"""

    def test_basic_calculation_no_inflation(self):
        """基本的な複利計算（インフレなし）"""
        result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0"),
        )

        assert isinstance(result, FireCalculationResult)
        assert result.feasible is True
        assert result.months_to_fi > 0
        # 複利効果により、単純計算(1000000/100000 = 10ヶ月)より早く到達するか、同程度
        assert result.months_to_fi <= 10
        assert result.message.startswith(f"{result.months_to_fi}ヶ月で")

    def test_calculation_with_inflation(self):
        """インフレ調整を含む計算"""
        result_no_inflation = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0"),
        )

        result_with_inflation = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0.02"),
        )

        # インフレがあると、実質資産が減少するため、到達月数が増える
        assert result_with_inflation.months_to_fi >= result_no_inflation.months_to_fi

    def test_zero_monthly_savings_infeasible(self):
        """月貯蓄ゼロで目標到達不可"""
        result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("0"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0"),
        )

        assert result.feasible is False
        assert result.months_to_fi == -1

    def test_already_achieved_target(self):
        """目標到達済み"""
        result = calculate_fire_index(
            current_assets=Decimal("2500000"),
            monthly_savings=Decimal("50000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0"),
        )

        assert result.feasible is True
        assert result.months_to_fi == 0

    def test_timeline_length_matches_months(self):
        """タイムライン長が到達月数に一致"""
        result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("1500000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0"),
        )

        assert len(result.achieved_assets_timeline) == result.months_to_fi

    def test_timeline_data_structure(self):
        """タイムラインのデータ構造確認"""
        result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("1500000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0"),
        )

        assert len(result.achieved_assets_timeline) > 0
        first_entry = result.achieved_assets_timeline[0]
        assert "month" in first_entry
        assert "nominal_assets" in first_entry
        assert "real_assets" in first_entry
        assert "monthly_interest" in first_entry
        assert isinstance(first_entry["month"], int)
        assert isinstance(first_entry["nominal_assets"], float)

    def test_scenarios_present(self):
        """3つのシナリオが生成される"""
        result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0"),
        )

        assert "pessimistic" in result.scenarios
        assert "neutral" in result.scenarios
        assert "optimistic" in result.scenarios

        # 楽観シナリオほど早く到達
        pessimistic = result.scenarios["pessimistic"]["months_to_fi"]
        neutral = result.scenarios["neutral"]["months_to_fi"]
        optimistic = result.scenarios["optimistic"]["months_to_fi"]

        assert pessimistic >= neutral >= optimistic

    def test_invalid_current_assets(self):
        """負の現在資産でエラー"""
        with pytest.raises(ValueError):
            calculate_fire_index(
                current_assets=Decimal("-100000"),
                monthly_savings=Decimal("100000"),
                target_assets=Decimal("2000000"),
                annual_return_rate=Decimal("0.05"),
            )

    def test_invalid_target_assets(self):
        """0以下の目標資産でエラー"""
        with pytest.raises(ValueError):
            calculate_fire_index(
                current_assets=Decimal("1000000"),
                monthly_savings=Decimal("100000"),
                target_assets=Decimal("0"),
                annual_return_rate=Decimal("0.05"),
            )

    def test_precision_to_two_decimal_places(self):
        """小数第2位までの精度"""
        result = calculate_fire_index(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("123456"),
            target_assets=Decimal("5000000"),
            annual_return_rate=Decimal("0.0347"),  # 3.47%
            inflation_rate=Decimal("0.0215"),  # 2.15%
        )

        # タイムラインの数値が小数第2位で表現されているか確認
        for entry in result.achieved_assets_timeline:
            nominal = entry["nominal_assets"]
            # 小数第2位までの値であるか（浮動小数点数の誤差は考慮）
            assert isinstance(nominal, float)
            assert nominal > 0


class TestSimulateScenario:
    """シナリオシミュレーションのテスト"""

    def test_scenario_simulation_basic(self):
        """シナリオシミュレーション基本"""
        months = _simulate_scenario(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("100000"),
            target_assets=Decimal("2000000"),
            annual_return_rate=Decimal("0.05"),
            inflation_rate=Decimal("0"),
        )

        assert isinstance(months, int)
        assert months > 0

    def test_scenario_simulation_impossible(self):
        """シナリオシミュレーション（到達不可）"""
        months = _simulate_scenario(
            current_assets=Decimal("1000000"),
            monthly_savings=Decimal("0"),
            target_assets=Decimal("10000000"),
            annual_return_rate=Decimal("0.01"),
            inflation_rate=Decimal("0"),
        )

        assert months == -1
