"""
Analysis tools (formerly phase16_tools).

Public API for income/savings/real-estate/FIRE simulations.
"""

from datetime import date
from decimal import Decimal

from ..analysis.enhanced_fire_simulator import (
    EnhancedFIRESimulator,
    FIREScenario,
    FIREType,
)
from ..analysis.income_analyzer import IncomeAnalyzer
from ..analysis.real_estate_cashflow_analyzer import RealEstateCashflowAnalyzer
from ..analysis.savings_rate_calculator import SavingsRateCalculator
from ..dataloader import HouseholdDataLoader


class AnalysisTools:
    """Top-level tools facade for analysis APIs."""

    def __init__(self) -> None:
        self.data_loader = HouseholdDataLoader()
        self.income_analyzer = IncomeAnalyzer(self.data_loader)
        self.savings_calculator = SavingsRateCalculator(
            self.income_analyzer, self.data_loader
        )
        self.re_analyzer = RealEstateCashflowAnalyzer(
            self.income_analyzer, self.data_loader
        )
        self.fire_simulator = EnhancedFIRESimulator()

    # Income APIs
    def get_income_summary(self, year: int, month: int) -> dict:
        summary = self.income_analyzer.get_monthly_summary(year, month)
        return summary.to_dict()

    def get_annual_income_summary(self, year: int) -> dict:
        summary = self.income_analyzer.get_annual_summary(year)
        return summary.to_dict()

    # Savings rate APIs
    def get_savings_rate(self, year: int, month: int) -> dict:
        metrics = self.savings_calculator.calculate_monthly_savings_rate(year, month)
        return metrics.to_dict()

    def get_savings_rate_trend(self, start_date: str, end_date: str) -> dict:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        metrics_list = self.savings_calculator.get_savings_rate_trend(start, end)
        return {
            "start_date": start_date,
            "end_date": end_date,
            "trend": [m.to_dict() for m in metrics_list],
        }

    # Real-estate cashflow APIs
    def get_real_estate_cashflow(
        self,
        start_date: str,
        end_date: str,
        property_id: str | None = None,
    ) -> dict:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        cashflow = self.re_analyzer.calculate_cashflow(start, end, property_id)
        return cashflow.to_dict()

    # FIRE simulation APIs
    def simulate_fire_scenarios(self, scenarios: list[dict]) -> dict:
        fire_scenarios = []
        for s in scenarios:
            initial_assets = s.get("initial_assets") or s.get("current_assets")
            fire_scenarios.append(
                FIREScenario(
                    name=s["name"],
                    fire_type=FIREType[s["fire_type"]],
                    initial_assets=Decimal(str(initial_assets)),
                    monthly_savings=Decimal(str(s["monthly_savings"])),
                    annual_expense=Decimal(str(s["annual_expense"])),
                    annual_return_rate=Decimal(str(s["annual_return_rate"])),
                    inflation_rate=Decimal(str(s.get("inflation_rate", "0"))),
                    passive_income=Decimal(str(s.get("passive_income", "0"))),
                    part_time_income=(
                        Decimal(str(s["part_time_income"]))
                        if s.get("part_time_income")
                        else None
                    ),
                    side_income=(
                        Decimal(str(s["side_income"])) if s.get("side_income") else None
                    ),
                )
            )

        results = []
        for scenario in fire_scenarios:
            target = self.fire_simulator.calculate_fire_target(
                fire_type=scenario.fire_type,
                annual_expense=scenario.annual_expense,
                annual_return_rate=scenario.annual_return_rate,
                passive_income=scenario.passive_income,
                part_time_income=scenario.part_time_income,
                side_income=scenario.side_income,
            )
            months = 0
            current = scenario.initial_assets
            while current < target and months < 600:
                current = (
                    current
                    * (Decimal("1") + scenario.annual_return_rate / Decimal("12"))
                    + scenario.monthly_savings
                )
                months += 1

            # Let EnhancedFIRESimulator build consistent result dict
            result = self.fire_simulator.simulate_scenario(scenario)
            results.append(result)

        comparison = self.fire_simulator.compare_scenarios(results)
        return {
            "scenarios": [r.to_dict() for r in results],
            "comparison": comparison,
        }

    def what_if_fire_simulation(self, base_scenario: dict, changes: dict) -> dict:
        initial_assets = base_scenario.get("initial_assets") or base_scenario.get(
            "current_assets"
        )
        if initial_assets is None:
            raise ValueError(
                "initial_assets or current_assets is required in base_scenario"
            )

        fire_base = FIREScenario(
            name=base_scenario["name"],
            fire_type=FIREType[base_scenario["fire_type"]],
            initial_assets=Decimal(str(initial_assets)),
            monthly_savings=Decimal(str(base_scenario["monthly_savings"])),
            annual_expense=Decimal(str(base_scenario["annual_expense"])),
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

        summary: dict[str, object] = {}
        for key, new_val in fire_changes.items():
            if hasattr(fire_base, key):
                old_val = getattr(fire_base, key)
                summary[f"{key}_before"] = (
                    float(old_val) if isinstance(old_val, Decimal) else old_val
                )
                summary[f"{key}_after"] = (
                    float(new_val) if isinstance(new_val, Decimal) else new_val
                )
        if isinstance(result, dict) and "impact" in result:
            summary.update({"impact": result["impact"]})
        return summary if summary else result

    def generate_comprehensive_cashflow_report(
        self, year: int, output_format: str = "markdown"
    ) -> dict:
        income_summary = self.income_analyzer.get_annual_summary(year)
        monthly_metrics = []
        for month in range(1, 13):
            try:
                metrics = self.savings_calculator.calculate_monthly_savings_rate(
                    year, month
                )
                monthly_metrics.append(metrics)
            except FileNotFoundError:
                continue
        re_cashflow = self.re_analyzer.calculate_cashflow(
            date(year, 1, 1), date(year, 12, 31)
        )

        if output_format == "markdown":
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
        return {"format": output_format, "content": report}

    def _format_markdown_report(self, year, income_summary, monthly_metrics, re) -> str:
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
                f"- 収入: ¥{re.income:,.0f}",
                f"- 支出: ¥{re.expense:,.0f}",
                f"- ネットキャッシュフロー: ¥{re.net_cashflow:,.0f}",
            ]
        )
        if re.roi:
            lines.append(f"- ROI: {re.roi}%")
        return "\n".join(lines)


_analysis_tools = AnalysisTools()


def get_income_summary(year: int, month: int) -> dict:
    return _analysis_tools.get_income_summary(year, month)


def get_annual_income_summary(year: int) -> dict:
    return _analysis_tools.get_annual_income_summary(year)


def get_savings_rate(year: int, month: int) -> dict:
    return _analysis_tools.get_savings_rate(year, month)


def get_savings_rate_trend(start_date: str, end_date: str) -> dict:
    return _analysis_tools.get_savings_rate_trend(start_date, end_date)


def get_real_estate_cashflow(
    start_date: str,
    end_date: str,
    property_id: str | None = None,
) -> dict:
    return _analysis_tools.get_real_estate_cashflow(start_date, end_date, property_id)


def simulate_fire_scenarios(scenarios: list[dict]) -> dict:
    return _analysis_tools.simulate_fire_scenarios(scenarios)


def what_if_fire_simulation(base_scenario: dict, changes: dict) -> dict:
    return _analysis_tools.what_if_fire_simulation(base_scenario, changes)


def generate_comprehensive_cashflow_report(
    year: int, output_format: str = "markdown"
) -> dict:
    return _analysis_tools.generate_comprehensive_cashflow_report(year, output_format)


__all__ = [
    "generate_comprehensive_cashflow_report",
    "get_annual_income_summary",
    "get_income_summary",
    "get_real_estate_cashflow",
    "get_savings_rate",
    "get_savings_rate_trend",
    "simulate_fire_scenarios",
    "what_if_fire_simulation",
]
