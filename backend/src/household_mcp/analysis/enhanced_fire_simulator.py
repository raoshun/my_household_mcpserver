"""
EnhancedFIRESimulator - 強化FIREシミュレーター

Phase 16で実装: 収入データを活用した高度なFIREシミュレーション
- 4種類のFIREタイプ（標準/コースト/バリスタ/サイド）
- 受動的収入を考慮した目標資産額の再計算
- 複数シナリオの比較と推奨
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum

# 金額精度定義
_MONEY_Q = Decimal("0.01")
_PERCENT_Q = Decimal("0.01")


class FIREType(Enum):
    """FIREタイプ定義"""

    STANDARD = "標準FIRE"
    COAST = "コーストFIRE"
    BARISTA = "バリスタFIRE"
    SIDE = "サイドFIRE"


@dataclass
class FIREScenario:
    """FIREシナリオ設定"""

    name: str
    fire_type: FIREType
    initial_assets: Decimal
    monthly_savings: Decimal
    annual_return_rate: Decimal
    inflation_rate: Decimal
    passive_income: Decimal
    part_time_income: Decimal | None = None
    side_income: Decimal | None = None
    expense_growth_rate: Decimal | None = None


@dataclass
class FIRESimulationResult:
    """FIREシミュレーション結果"""

    scenario_name: str
    fire_type: FIREType
    target_assets: Decimal
    months_to_fire: int
    achievement_date: str
    total_savings_needed: Decimal
    asset_timeline: list[dict[str, Decimal]]
    risk_assessment: str

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "scenario_name": self.scenario_name,
            "fire_type": self.fire_type.value,
            "target_assets": float(self.target_assets),
            "months_to_fire": self.months_to_fire,
            "achievement_date": self.achievement_date,
            "total_savings_needed": float(self.total_savings_needed),
            "asset_timeline": [
                {k: float(v) for k, v in point.items()} for point in self.asset_timeline
            ],
            "risk_assessment": self.risk_assessment,
        }


class EnhancedFIRESimulator:
    """強化FIREシミュレーター"""

    # 4%ルールの逆数（25倍）
    STANDARD_MULTIPLIER = Decimal("25")
    # コーストFIREの老後開始年齢
    COAST_FIRE_AGE = 65
    # 現在年齢（デフォルト）
    DEFAULT_CURRENT_AGE = 35

    def __init__(self):
        """初期化"""
        pass

    def calculate_fire_target(
        self,
        fire_type: FIREType,
        annual_expense: Decimal,
        passive_income: Decimal = Decimal("0"),
        part_time_income: Decimal | None = None,
        side_income: Decimal | None = None,
        current_age: int = DEFAULT_CURRENT_AGE,
        current_assets: Decimal = Decimal("0"),
        annual_return_rate: Decimal = Decimal("0.05"),
    ) -> Decimal:
        """
        FIREタイプ別の目標資産額を計算

        Args:
            fire_type: FIREタイプ
            annual_expense: 年間支出
            passive_income: 年間受動的収入
            part_time_income: パートタイム年収（バリスタFIREのみ）
            side_income: 副業年収（サイドFIREのみ）
            current_age: 現在年齢（コーストFIREのみ）
            current_assets: 現在資産額（コーストFIREのみ）
            annual_return_rate: 年間運用利回り（コーストFIREのみ）

        Returns:
            目標資産額

        Raises:
            ValueError: 無効なパラメータ

        """
        if annual_expense <= 0:
            raise ValueError("年間支出は正の値である必要があります")

        # 受動的収入考慮
        net_expense = annual_expense - passive_income
        if net_expense <= 0:
            # 受動的収入で全支出カバー可能
            return Decimal("0").quantize(_MONEY_Q)

        if fire_type == FIREType.STANDARD:
            # 標準FIRE: 年間支出 × 25
            target = net_expense * self.STANDARD_MULTIPLIER

        elif fire_type == FIREType.COAST:
            # コーストFIRE: 老後必要額から現資産の将来価値を引いた額
            years_to_retirement = self.COAST_FIRE_AGE - current_age
            if years_to_retirement <= 0:
                raise ValueError("既に老後年齢に達しています")

            # 老後必要額（25年分）
            retirement_needed = annual_expense * self.STANDARD_MULTIPLIER

            # 現資産の将来価値
            future_value = current_assets * (
                (Decimal("1") + annual_return_rate) ** years_to_retirement
            )

            # 必要な追加資産
            target = max(Decimal("0"), retirement_needed - future_value)

        elif fire_type == FIREType.BARISTA:
            # バリスタFIRE: (年間支出 - パートタイム収入) × 25
            if part_time_income is None:
                raise ValueError("バリスタFIREにはパートタイム収入が必要です")

            net_expense_barista = net_expense - part_time_income
            if net_expense_barista <= 0:
                return Decimal("0").quantize(_MONEY_Q)

            target = net_expense_barista * self.STANDARD_MULTIPLIER

        elif fire_type == FIREType.SIDE:
            # サイドFIRE: (年間支出 - 副業収入) × 25
            if side_income is None:
                raise ValueError("サイドFIREには副業収入が必要です")

            net_expense_side = net_expense - side_income
            if net_expense_side <= 0:
                return Decimal("0").quantize(_MONEY_Q)

            target = net_expense_side * self.STANDARD_MULTIPLIER

        else:
            raise ValueError(f"未サポートのFIREタイプ: {fire_type}")

        return target.quantize(_MONEY_Q, rounding=ROUND_HALF_UP)

    def simulate_scenario(self, scenario: FIREScenario) -> FIRESimulationResult:
        """
        単一シナリオのFIREシミュレーションを実行

        Args:
            scenario: シナリオ設定

        Returns:
            シミュレーション結果

        """
        # 目標資産額を計算
        target_assets = self.calculate_fire_target(
            fire_type=scenario.fire_type,
            annual_expense=(scenario.passive_income * Decimal("25")),
            # Note: ここでは簡易的に受動的収入をベースに支出を推定
            passive_income=scenario.passive_income,
            part_time_income=scenario.part_time_income,
            side_income=scenario.side_income,
        )

        # 月次シミュレーション
        current_assets = scenario.initial_assets
        month = 0
        timeline = []

        # 月利計算
        monthly_return = (Decimal("1") + scenario.annual_return_rate) ** (
            Decimal("1") / Decimal("12")
        ) - Decimal("1")

        while current_assets < target_assets and month < 1200:  # 最大100年
            # 資産増加: 貯蓄 + 運用益
            monthly_return_amount = current_assets * monthly_return
            current_assets += scenario.monthly_savings + monthly_return_amount

            month += 1

            # タイムライン記録（12ヶ月ごと）
            if month % 12 == 0:
                timeline.append(
                    {
                        "month": month,
                        "assets": current_assets.quantize(_MONEY_Q),
                    }
                )

        # 到達日計算
        achievement_date = (date.today() + timedelta(days=30 * month)).strftime("%Y-%m")

        # 総貯蓄額
        total_savings = scenario.monthly_savings * month

        # リスク評価
        risk = self._assess_risk(scenario, month)

        return FIRESimulationResult(
            scenario_name=scenario.name,
            fire_type=scenario.fire_type,
            target_assets=target_assets,
            months_to_fire=month,
            achievement_date=achievement_date,
            total_savings_needed=total_savings.quantize(_MONEY_Q),
            asset_timeline=timeline,
            risk_assessment=risk,
        )

    def simulate_scenarios(
        self, scenarios: list[FIREScenario]
    ) -> list[FIRESimulationResult]:
        """
        複数シナリオを一括シミュレーション

        Args:
            scenarios: シナリオリスト（最大5件）

        Returns:
            シミュレーション結果リスト

        Raises:
            ValueError: シナリオ数が上限超過

        """
        if len(scenarios) > 5:
            raise ValueError("シナリオは最大5件まで対応")

        return [self.simulate_scenario(s) for s in scenarios]

    def compare_scenarios(self, results: list[FIRESimulationResult]) -> dict:
        """
        シナリオ比較レポートを生成

        Args:
            results: シミュレーション結果リスト

        Returns:
            比較レポート

        """
        if not results:
            return {"error": "比較対象のシナリオがありません"}

        # 最速到達シナリオ
        fastest = min(results, key=lambda r: r.months_to_fire)

        # 最小貯蓄シナリオ
        min_savings = min(results, key=lambda r: r.total_savings_needed)

        # 比較サマリー
        comparison = {
            "fastest_scenario": {
                "name": fastest.scenario_name,
                "months": fastest.months_to_fire,
                "achievement_date": fastest.achievement_date,
            },
            "min_savings_scenario": {
                "name": min_savings.scenario_name,
                "total_savings": float(min_savings.total_savings_needed),
            },
            "all_scenarios": [
                {
                    "name": r.scenario_name,
                    "months_to_fire": r.months_to_fire,
                    "total_savings": float(r.total_savings_needed),
                    "risk": r.risk_assessment,
                }
                for r in results
            ],
        }

        return comparison

    def what_if_simulation(
        self, base_scenario: FIREScenario, changes: dict[str, Decimal]
    ) -> dict:
        """
        What-Ifシミュレーション

        Args:
            base_scenario: ベースシナリオ
            changes: 変更パラメータ（例: {"monthly_savings": 50000}）

        Returns:
            変更前後の比較結果

        """
        # ベースシナリオの結果
        base_result = self.simulate_scenario(base_scenario)

        # 変更後シナリオ作成
        modified_scenario = FIREScenario(
            name=f"{base_scenario.name} (変更後)",
            fire_type=base_scenario.fire_type,
            initial_assets=changes.get("initial_assets", base_scenario.initial_assets),
            monthly_savings=changes.get(
                "monthly_savings", base_scenario.monthly_savings
            ),
            annual_return_rate=changes.get(
                "annual_return_rate", base_scenario.annual_return_rate
            ),
            inflation_rate=changes.get("inflation_rate", base_scenario.inflation_rate),
            passive_income=changes.get("passive_income", base_scenario.passive_income),
            part_time_income=changes.get(
                "part_time_income", base_scenario.part_time_income
            ),
            side_income=changes.get("side_income", base_scenario.side_income),
        )

        modified_result = self.simulate_scenario(modified_scenario)

        # 差分計算
        months_diff = base_result.months_to_fire - modified_result.months_to_fire
        savings_diff = (
            base_result.total_savings_needed - modified_result.total_savings_needed
        )

        return {
            "base": base_result.to_dict(),
            "modified": modified_result.to_dict(),
            "impact": {
                "months_saved": months_diff,
                "savings_difference": float(savings_diff),
                "improvement_pct": float(
                    (
                        months_diff / base_result.months_to_fire * Decimal("100")
                    ).quantize(_PERCENT_Q)
                ),
            },
        }

    def _assess_risk(self, scenario: FIREScenario, months_to_fire: int) -> str:
        """
        リスク評価

        Args:
            scenario: シナリオ
            months_to_fire: FIRE到達月数

        Returns:
            リスク評価文字列

        """
        # 簡易的なリスク評価
        years_to_fire = months_to_fire / 12

        if years_to_fire > 30:
            return "高リスク: 30年超の長期計画"
        elif years_to_fire > 20:
            return "中リスク: 20-30年の計画"
        elif years_to_fire > 10:
            return "低リスク: 10-20年の計画"
        else:
            return "最低リスク: 10年以内の計画"
