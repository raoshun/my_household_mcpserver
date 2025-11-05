"""Analysis modules for the household MCP server."""

from .expense_classifier import ClassificationResult, ExpenseClassifier
from .financial_independence import FinancialIndependenceAnalyzer
from .fire_calculator import FIRECalculator
from .trend_statistics import GrowthRateAnalysis, ProjectionScenario, TrendStatistics
from .trends import CategoryTrendAnalyzer, TrendMetrics

__all__ = [
    "CategoryTrendAnalyzer",
    "ClassificationResult",
    "ExpenseClassifier",
    "FIRECalculator",
    "FinancialIndependenceAnalyzer",
    "GrowthRateAnalysis",
    "ProjectionScenario",
    "TrendMetrics",
    "TrendStatistics",
]
