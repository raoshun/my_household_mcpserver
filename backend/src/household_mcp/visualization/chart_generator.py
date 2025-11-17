"""
Chart generation module for household budget visualization.

This module provides ChartGenerator class as a factory that delegates
to specialized chart generators for creating various types of charts
from household data using matplotlib with Japanese font support.
"""

from __future__ import annotations

import io
from typing import Any

try:
    import pandas as pd

    HAS_VISUALIZATION_DEPS = True
except ImportError:
    HAS_VISUALIZATION_DEPS = False

from ..exceptions import ChartGenerationError
from .bar_chart import BarChartGenerator
from .line_chart import LineChartGenerator
from .pie_chart import PieChartGenerator


class ChartGenerator:
    """
    Chart generator factory for household budget data visualization.

    This class delegates to specialized chart generators (pie, bar, line)
    with proper Japanese font support and consistent styling.
    Maintains backward compatibility with the original single-class API.
    """

    def __init__(self, font_path: str | None = None):
        """
        Initialize chart generator factory.

        Args:
            font_path: Optional path to Japanese font file.
                      If None, attempts to auto-detect system fonts.

        """
        if not HAS_VISUALIZATION_DEPS:
            raise ChartGenerationError(
                "Visualization dependencies not installed. "
                "Install with: "
                "pip install household-mcp-server[visualization]"
            )

        # Initialize specialized generators with shared font config
        self._pie_generator = PieChartGenerator(font_path)
        self._line_generator = LineChartGenerator(font_path)
        self._bar_generator = BarChartGenerator(font_path)

        # Store font_path for API compatibility
        self.font_path = self._pie_generator.font_path

    def create_monthly_pie_chart(
        self,
        data: pd.DataFrame,
        title: str = "月次支出構成",
        **options: Any,
    ) -> io.BytesIO:
        """
        Create pie chart for monthly expense breakdown.

        Args:
            data: DataFrame with category and amount columns
            title: Chart title
            **options: Additional chart options (image_size, colors, etc.)

        Returns:
            BytesIO buffer containing the chart image

        """
        return self._pie_generator.create_monthly_pie_chart(data, title, **options)

    def create_category_trend_line(
        self,
        data: pd.DataFrame,
        category: str | None = None,
        title: str | None = None,
        **options: Any,
    ) -> io.BytesIO:
        """
        Create line chart for category trend over time.

        Args:
            data: DataFrame with date/month and amount columns
            category: Category name for title
            title: Custom chart title
            **options: Additional chart options

        Returns:
            BytesIO buffer containing the chart image

        """
        return self._line_generator.create_category_trend_line(
            data, category, title, **options
        )

    def create_comparison_bar_chart(
        self,
        data: pd.DataFrame,
        title: str = "カテゴリ別比較",
        **options: Any,
    ) -> io.BytesIO:
        """
        Create bar chart for category comparison.

        Args:
            data: DataFrame with category and amount columns
            title: Chart title
            **options: Additional chart options

        Returns:
            BytesIO buffer containing the chart image

        """
        return self._bar_generator.create_comparison_bar_chart(data, title, **options)


# Export all chart generators for direct use
__all__ = [
    "BarChartGenerator",
    "ChartGenerator",
    "LineChartGenerator",
    "PieChartGenerator",
]
