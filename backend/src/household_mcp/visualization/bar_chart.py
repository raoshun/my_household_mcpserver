"""Bar chart generator for category comparison."""

from __future__ import annotations

import io
import warnings
from typing import TYPE_CHECKING, Any

try:
    import matplotlib.pyplot as plt
    import pandas as pd
    from matplotlib.ticker import FuncFormatter
except ImportError:
    pass

from ..exceptions import ChartGenerationError
from .base import BaseChartGenerator

if TYPE_CHECKING:
    from collections.abc import Sequence

    from matplotlib.axes import Axes


class BarChartGenerator(BaseChartGenerator):
    """Generator for bar charts showing category comparisons."""

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
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"Glyph .* missing from current font",
                    category=UserWarning,
                )
                # Figure
                fig, ax = self._create_figure(options.get("image_size", "800x600"))

                # Prepare data and columns
                chart_data = data.copy()
                (
                    category_col,
                    amount_col,
                ) = self._infer_category_amount_columns(chart_data)
                font_prop = self._get_font_properties()
                if font_prop is None and self.font_path is None:
                    warnings.warn(
                        "Japanese font not found. "
                        "Text may not render correctly. "
                        "Install a CJK font (e.g., 'Noto Sans CJK JP').",
                        UserWarning,
                        stacklevel=2,
                    )

                # Group and sort (ascending for horizontal bar)
                chart_data = (
                    chart_data.groupby(category_col)[amount_col].sum().reset_index()
                )
                chart_data = chart_data.sort_values(amount_col, ascending=True)

                # Bars
                colors = self._get_colors(len(chart_data))
                font_prop = self._get_font_properties()
                bars = ax.barh(
                    chart_data[category_col],
                    chart_data[amount_col],
                    color=colors,
                )

                # Labels
                self._render_bar_value_labels(ax, bars, font_prop)

                # Titles/labels
                ax.set_title(
                    title,
                    fontsize=16,
                    fontweight="bold",
                    pad=20,
                    fontproperties=font_prop if font_prop else None,
                )
                ax.set_xlabel(
                    "金額 (円)",
                    fontsize=12,
                    fontproperties=font_prop if font_prop else None,
                )

                # Axis formatting
                self._apply_currency_formatter(ax)
                ax.grid(True, alpha=0.3, axis="x")
                plt.tight_layout()

                # Save
                return self._save_figure_to_buffer(fig)

        except Exception as e:
            plt.close("all")
            msg = f"Failed to create bar chart: {e!s}"
            raise ChartGenerationError(msg) from e

    def _infer_category_amount_columns(self, df: pd.DataFrame) -> tuple[str, str]:
        """
        Infer category and amount column names from DataFrame.

        Args:
            df: Input DataFrame

        Returns:
            Tuple of (category_col, amount_col)

        Raises:
            ChartGenerationError: If columns cannot be identified

        """
        category_col = self._infer_column(
            list(df.columns), ["カテゴリ", "category", "項目", "大項目"]
        )
        amount_col = self._infer_column(list(df.columns), ["金額", "amount", "円"])
        if not category_col or not amount_col:
            msg = "Cannot identify category and amount columns"
            raise ChartGenerationError(msg)
        return category_col, amount_col

    def _render_bar_value_labels(
        self, ax: Axes, bars: Sequence[Any], font_prop: Any
    ) -> None:
        """
        Render value labels at the end of horizontal bars.

        Args:
            ax: Matplotlib axes
            bars: Bar container objects
            font_prop: Font properties to apply

        """
        for b in bars:
            value = b.get_width()
            ax.text(
                value,
                b.get_y() + b.get_height() / 2,
                f"{int(value):,}円",
                ha="left",
                va="center",
                fontweight="bold",
                fontproperties=font_prop if font_prop else None,
            )

    def _apply_currency_formatter(self, ax: Axes) -> None:
        """
        Apply thousands separator + 円 unit to X axis.

        Args:
            ax: Matplotlib axes

        """
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x):,}円"))
