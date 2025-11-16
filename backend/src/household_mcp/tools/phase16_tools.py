"""
Phase 16 MCP Tools - 収入分析・強化FIRE計算ツール

FR-034: MCPツール実装
- 収入分析ツール（月次/年次サマリー）
- 貯蓄率分析ツール（月次/推移）
- 不動産キャッシュフローツール
- 強化FIREシミュレーションツール
"""

from datetime import date, datetime
from decimal import Decimal

from household_mcp.analysis.enhanced_fire_simulator import (
    EnhancedFIRESimulator,
    FIREScenario,
    FIRESimulationResult,
    FIREType,
)
from household_mcp.analysis.income_analyzer import IncomeAnalyzer
from household_mcp.analysis.real_estate_cashflow_analyzer import (
    RealEstateCashflowAnalyzer,
)
from household_mcp.analysis.savings_rate_calculator import SavingsRateCalculator
from household_mcp.dataloader import HouseholdDataLoader


class Phase16Tools:
    """Phase 16 MCP Tools wrapper"""

    def __init__(self):
        """初期化"""
        self.data_loader = HouseholdDataLoader()
        self.income_analyzer = IncomeAnalyzer(self.data_loader)
        self.savings_calculator = SavingsRateCalculator(
            self.income_analyzer, self.data_loader
        )
        self.re_analyzer = RealEstateCashflowAnalyzer(
            self.income_analyzer, self.data_loader
        )
        self.fire_simulator = EnhancedFIRESimulator()

    # ==================== 収入分析ツール ====================

    def get_income_summary(self, year: int, month: int) -> dict:
        """
        月次収入サマリーを取得

        Args:
            year: 対象年
            month: 対象月

        Returns:
            収入サマリー辞書

        """
        summary = self.income_analyzer.get_monthly_summary(year, month)
        return summary.to_dict()

    def get_annual_income_summary(self, year: int) -> dict:
        """
        年次収入サマリーを取得

        Args:
            year: 対象年

        Returns:
            年次収入サマリー辞書

        """
        summary = self.income_analyzer.get_annual_summary(year)
        return summary.to_dict()

    # ==================== 貯蓄率分析ツール ====================

    def get_savings_rate(self, year: int, month: int) -> dict:
        """
        月次貯蓄率を取得

        Args:
            year: 対象年
            month: 対象月

        Returns:
            貯蓄率メトリクス辞書

        """
        metrics = self.savings_calculator.calculate_monthly_savings_rate(year, month)
        return metrics.to_dict()

    def get_savings_rate_trend(self, start_date: str, end_date: str) -> dict:
        """
        貯蓄率推移を取得

        Args:
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）

        Returns:
            貯蓄率推移辞書

        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        metrics_list = self.savings_calculator.get_savings_rate_trend(start, end)
        return {
            "start_date": start_date,
            "end_date": end_date,
            "trend": [m.to_dict() for m in metrics_list],
        }

    # ==================== 不動産キャッシュフローツール ====================

    def get_real_estate_cashflow(
        self,
        start_date: str,
        end_date: str,
        property_id: str | None = None,
    ) -> dict:
        """
        不動産キャッシュフローを取得

        Args:
            start_date: 開始日（YYYY-MM-DD）
            end_date: 終了日（YYYY-MM-DD）
            property_id: 物件ID（省略時は全物件合計）

        Returns:
            キャッシュフロー辞書

        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        cashflow = self.re_analyzer.calculate_cashflow(start, end, property_id)
        return cashflow.to_dict()

    # ==================== 強化FIREシミュレーションツール ====================

    def simulate_fire_scenarios(self, scenarios: list[dict]) -> dict:
        """
        複数シナリオを一括シミュレーション

        Args:
            scenarios: シナリオリスト（最大5件）

        Returns:
            シミュレーション結果辞書

        """
        fire_scenarios = []
        for s in scenarios:
            # current_assetsとinitial_assetsのどちらでも受け入れる
            initial_assets = s.get("initial_assets") or s.get("current_assets")
            # annual_expenseを保持（FIREScenarioには含まれないので別途管理）
            annual_expense = Decimal(str(s["annual_expense"]))
            fire_scenarios.append(
                (
                    FIREScenario(
                        name=s["name"],
                        fire_type=FIREType[s["fire_type"]],
                        initial_assets=Decimal(str(initial_assets)),
                        monthly_savings=Decimal(str(s["monthly_savings"])),
                        annual_return_rate=Decimal(str(s["annual_return_rate"])),
                        inflation_rate=Decimal(str(s.get("inflation_rate", "0"))),
                        passive_income=Decimal(str(s.get("passive_income", "0"))),
                        part_time_income=(
                            Decimal(str(s["part_time_income"]))
                            if s.get("part_time_income")
                            else None
                        ),
                        side_income=(
                            Decimal(str(s["side_income"]))
                            if s.get("side_income")
                            else None
                        ),
                    ),
                    annual_expense,
                )
            )

        # simulate_scenariosは単一annual_expenseを想定しているため、
        # 各シナリオ個別にシミュレーション
        results = []
        for scenario, expense in fire_scenarios:
            # calculate_fire_targetを先に呼び、目標資産を設定
            target = self.fire_simulator.calculate_fire_target(
                fire_type=scenario.fire_type,
                annual_expense=expense,
                annual_return_rate=scenario.annual_return_rate,
                passive_income=scenario.passive_income,
                part_time_income=scenario.part_time_income,
                side_income=scenario.side_income,
            )
            # 簡易的なシミュレーション結果を作成
            months = 0
            current = scenario.initial_assets
            while current < target and months < 600:  # 最大50年
                current = (
                    current
                    * (Decimal("1") + scenario.annual_return_rate / Decimal("12"))
                    + scenario.monthly_savings
                )
                months += 1

            results.append(
                FIRESimulationResult(
                    scenario_name=scenario.name,
                    fire_type=scenario.fire_type,
                    target_assets=target,
                    months_to_fire=months,
                    achievement_date="",  # 省略
                    total_savings_needed=Decimal("0"),  # 省略
                    asset_timeline=[],  # 省略
                    risk_assessment="",  # 省略
                )
            )

        comparison = self.fire_simulator.compare_scenarios(results)

        return {
            "scenarios": [r.to_dict() for r in results],
            "comparison": comparison,
        }

    def what_if_fire_simulation(self, base_scenario: dict, changes: dict) -> dict:
        """
        What-Ifシミュレーションを実行

        Args:
            base_scenario: ベースシナリオ
            changes: 変更パラメータ

        Returns:
            変更前後の比較結果

        """
        fire_base = FIREScenario(
            name=base_scenario["name"],
            fire_type=FIREType[base_scenario["fire_type"]],
            initial_assets=Decimal(str(base_scenario["initial_assets"])),
            monthly_savings=Decimal(str(base_scenario["monthly_savings"])),
            annual_return_rate=Decimal(str(base_scenario["annual_return_rate"])),
            inflation_rate=Decimal(str(base_scenario["inflation_rate"])),
            passive_income=Decimal(str(base_scenario["passive_income"])),
            part_time_income=(
                Decimal(str(base_scenario["part_time_income"]))
                if base_scenario.get("part_time_income")
                else None
            ),
            side_income=(
                Decimal(str(base_scenario["side_income"]))
                if base_scenario.get("side_income")
                else None
            ),
        )

        fire_changes = {k: Decimal(str(v)) for k, v in changes.items()}

        result = self.fire_simulator.what_if_simulation(fire_base, fire_changes)
        return result

    # ==================== 統合レポートツール ====================

    def generate_comprehensive_cashflow_report(
        self, year: int, format: str = "markdown"
    ) -> dict:
        """
        年次総合キャッシュフローレポートを生成

        Args:
            year: 対象年
            format: 出力フォーマット（markdown/json）

        Returns:
            レポート辞書

        """
        # 年次収入サマリー
        income_summary = self.income_analyzer.get_annual_summary(year)

        # 年次貯蓄率（各月の平均）
        monthly_metrics = []
        for month in range(1, 13):
            try:
                metrics = self.savings_calculator.calculate_monthly_savings_rate(
                    year, month
                )
                monthly_metrics.append(metrics)
            except FileNotFoundError:
                continue

        # 不動産キャッシュフロー（年間）
        re_cashflow = self.re_analyzer.calculate_cashflow(
            date(year, 1, 1), date(year, 12, 31)
        )

        if format == "markdown":
            report = self._format_markdown_report(
                year, income_summary, monthly_metrics, re_cashflow
            )
        else:
            report = {
                "year": year,
                "income_summary": income_summary.to_dict(),
                "monthly_savings": [m.to_dict() for m in monthly_metrics],
                "real_estate_cashflow": re_cashflow.to_dict(),
            }

        return {"format": format, "content": report}

    def _format_markdown_report(
        self, year, income_summary, monthly_metrics, re_cashflow
    ) -> str:
        """Markdownレポート生成"""
        lines = [
            f"# {year}年度 総合キャッシュフローレポート",
            "",
            "## 収入サマリー",
            f"- 総収入: ¥{income_summary.total_income:,.0f}",
            f"- 月平均: ¥{income_summary.average_monthly:,.0f}",
            "",
            "### カテゴリ別内訳",
        ]

        for cat, amount in income_summary.category_breakdown.items():
            ratio = income_summary.category_ratios.get(cat, Decimal("0"))
            lines.append(f"- {cat}: ¥{amount:,.0f} ({ratio}%)")

        lines.extend(
            [
                "",
                "## 貯蓄率推移",
                f"- データ月数: {len(monthly_metrics)}ヶ月",
            ]
        )

        if monthly_metrics:
            avg_rate = sum(m.savings_rate for m in monthly_metrics) / len(
                monthly_metrics
            )
            lines.append(f"- 平均貯蓄率: {avg_rate:.2f}%")

        lines.extend(
            [
                "",
                "## 不動産キャッシュフロー",
                f"- 収入: ¥{re_cashflow.income:,.0f}",
                f"- 支出: ¥{re_cashflow.expense:,.0f}",
                f"- ネットキャッシュフロー: ¥{re_cashflow.net_cashflow:,.0f}",
            ]
        )

        if re_cashflow.roi:
            lines.append(f"- ROI: {re_cashflow.roi}%")

        return "\n".join(lines)


# グローバルインスタンス（MCPツール登録用）
_phase16_tools = Phase16Tools()


# MCPツール関数定義
def get_income_summary(year: int, month: int) -> dict:
    """月次収入サマリーを取得"""
    return _phase16_tools.get_income_summary(year, month)


def get_annual_income_summary(year: int) -> dict:
    """年次収入サマリーを取得"""
    return _phase16_tools.get_annual_income_summary(year)


def get_savings_rate(year: int, month: int) -> dict:
    """月次貯蓄率を取得"""
    return _phase16_tools.get_savings_rate(year, month)


def get_savings_rate_trend(start_date: str, end_date: str) -> dict:
    """貯蓄率推移を取得"""
    return _phase16_tools.get_savings_rate_trend(start_date, end_date)


def get_real_estate_cashflow(
    start_date: str,
    end_date: str,
    property_id: str | None = None,
) -> dict:
    """不動産キャッシュフローを取得"""
    return _phase16_tools.get_real_estate_cashflow(start_date, end_date, property_id)


def simulate_fire_scenarios(scenarios: list[dict]) -> dict:
    """複数シナリオを一括シミュレーション"""
    return _phase16_tools.simulate_fire_scenarios(scenarios)


def what_if_fire_simulation(base_scenario: dict, changes: dict) -> dict:
    """What-Ifシミュレーションを実行"""
    return _phase16_tools.what_if_fire_simulation(base_scenario, changes)


def generate_comprehensive_cashflow_report(year: int, format: str = "markdown") -> dict:
    """年次総合キャッシュフローレポートを生成"""
    return _phase16_tools.generate_comprehensive_cashflow_report(year, format)
