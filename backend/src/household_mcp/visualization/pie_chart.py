"""Pie chart generator for monthly expense breakdown."""

from __future__ import annotations

import io
import warnings
from typing import Any

try:
    import matplotlib.pyplot as plt
    import pandas as pd
    from matplotlib.text import Text
except ImportError:
    pass

from ..exceptions import ChartGenerationError
from .base import BaseChartGenerator


class PieChartGenerator(BaseChartGenerator):
    """Generator for pie charts showing monthly expense breakdown."""

    def create_monthly_pie_chart(
        self, data: pd.DataFrame, title: str = "月次支出構成", **options: Any
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
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"Glyph .* missing from current font",
                    category=UserWarning,
                )
                width, height = self._parse_image_size(
                    options.get("image_size", "800x600")
                )
                fig, ax = plt.subplots(figsize=(width / 100, height / 100))

                chart_data = self._prepare_pie_chart_data(data)
                font_prop = self._get_font_properties()
                if font_prop is None:
                    warnings.warn(
                        "Japanese font not found. "
                        "Text may not render correctly. "
                        "Install a CJK font (e.g., 'Noto Sans CJK JP').",
                        UserWarning,
                        stacklevel=2,
                    )
                colors = self._get_colors(len(chart_data))

                # Create pie chart
                labels = chart_data["category"].tolist()
                pie_result = ax.pie(
                    chart_data["amount"],
                    labels=labels,
                    colors=colors,
                    autopct="%1.1f%%",
                    startangle=90,
                    counterclock=False,
                )
                if len(pie_result) == 3:
                    _, texts, autotexts = pie_result
                    self._style_pie_labels(texts, autotexts, font_prop)
                else:
                    _, texts = pie_result
                    self._style_pie_labels(texts, [], font_prop)
                ax.set_title(
                    title,
                    fontsize=16,
                    fontweight="bold",
                    pad=20,
                    fontproperties=font_prop,
                )
                ax.axis("equal")

                return self._save_figure_to_buffer(fig)
        except Exception as e:
            plt.close("all")
            msg = f"Failed to create pie chart: {e!s}"
            raise ChartGenerationError(msg) from e

    def _prepare_pie_chart_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare and validate data for pie chart.

        Args:
            data: Input DataFrame with category and amount data

        Returns:
            Processed DataFrame with 'category' and 'amount' columns

        Raises:
            ChartGenerationError: If columns cannot be identified
                or no valid data

        """
        if {"category", "amount"}.issubset(data.columns):
            chart_data = data[["category", "amount"]].copy()
        else:
            amount_col = self._infer_column(
                list(data.columns), ["金額", "amount", "円"]
            )
            category_col = self._infer_column(
                list(data.columns), ["カテゴリ", "category", "項目", "大項目"]
            )
            if not amount_col or not category_col:
                raise ChartGenerationError(
                    "Cannot identify category and amount columns"
                )
            chart_data = data[[category_col, amount_col]].copy()
            chart_data.columns = ["category", "amount"]

        chart_data = chart_data[chart_data["amount"] > 0]
        grouped = chart_data.groupby("category", as_index=False)
        chart_data = grouped["amount"].sum()
        # Sort by amount descending
        chart_data = chart_data.sort_values("amount", ascending=False)

        if chart_data.empty:
            msg = "No positive amounts found for pie chart"
            raise ChartGenerationError(msg)

        return chart_data

    def _style_pie_labels(
        self,
        texts: list[Text],
        autotexts: list[Text],
        font_prop: Any,
    ) -> None:
        """
        Apply styling to pie chart labels and percentage texts.

        Args:
            texts: List of label text objects
            autotexts: List of autopct text objects (percentages)
            font_prop: Font properties to apply

        """
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")
            if font_prop:
                autotext.set_fontproperties(font_prop)
        for text in texts:
            if font_prop:
                text.set_fontproperties(font_prop)
