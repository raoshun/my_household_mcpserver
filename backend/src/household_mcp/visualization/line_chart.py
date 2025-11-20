"""Line chart generator for category trend over time."""

from __future__ import annotations

import io
import warnings
from typing import Any

try:
    import matplotlib.pyplot as plt
    import pandas as pd
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
except ImportError:
    pass

from ..exceptions import ChartGenerationError
from .base import BaseChartGenerator


class LineChartGenerator(BaseChartGenerator):
    """Generator for line charts showing trends over time."""

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
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"Glyph .* missing from current font",
                    category=UserWarning,
                )
                fig, ax = self._create_figure(options.get("image_size", "800x600"))
                (
                    trend_data,
                    time_col,
                    amount_col,
                ) = self._prepare_trend_line_data(data)

                ax.plot(
                    range(len(trend_data)),
                    trend_data[amount_col],
                    marker="o",
                    linewidth=2,
                    markersize=6,
                    color="#1f77b4",
                )

                font_prop = self._get_font_properties()
                if font_prop is None and self.font_path is None:
                    warnings.warn(
                        "Japanese font not found. "
                        "Text may not render correctly. "
                        "Install a CJK font (e.g., 'Noto Sans CJK JP').",
                        UserWarning,
                        stacklevel=2,
                    )
                self._configure_trend_axes(fig, ax, trend_data, time_col, font_prop)

                chart_title = title or (f"{category}の推移" if category else "支出推移")
                ax.set_title(
                    chart_title,
                    fontsize=16,
                    fontweight="bold",
                    pad=20,
                    fontproperties=font_prop if font_prop else None,
                )

                return self._save_figure_to_buffer(fig)

        except Exception as e:
            plt.close("all")
            msg = f"Failed to create line chart: {e!s}"
            raise ChartGenerationError(msg) from e

    def _prepare_trend_line_data(
        self, data: pd.DataFrame
    ) -> tuple[pd.DataFrame, str, str]:
        """
        Prepare data for trend line plotting.

        Args:
            data: Input DataFrame with time and amount columns

        Returns:
            Tuple of (trend_data, time_col, amount_col)

        Raises:
            ChartGenerationError: If columns cannot be identified

        """
        # Infer columns
        time_col = self._infer_column(
            list(data.columns), ["month", "date", "年月", "月", "期間"]
        )
        amount_col = self._infer_column(list(data.columns), ["金額", "amount", "円"])
        if not time_col or not amount_col:
            msg = "Cannot identify time and amount columns"
            raise ChartGenerationError(msg)

        df = data.copy()

        # Normalize time column to string labels like YYYY-MM
        try:
            # Try datetime conversion
            dt = pd.to_datetime(df[time_col], errors="coerce")
            # If any valid dates, use YYYY-MM period string
            if dt.notna().any():
                df["__month_label__"] = dt.dt.to_period("M").astype(str)
                time_label_col = "__month_label__"
            else:
                # Assume already like 'YYYY-MM' strings
                df["__month_label__"] = df[time_col].astype(str)
                time_label_col = "__month_label__"
        except Exception:
            df["__month_label__"] = df[time_col].astype(str)
            time_label_col = "__month_label__"

        # Aggregate by month label
        trend = df.groupby(time_label_col, as_index=False)[amount_col].sum().copy()

        # Sort by time label (parse back to period for robust sort)
        try:
            trend["__sort_key__"] = pd.PeriodIndex(trend[time_label_col], freq="M")
            trend = trend.sort_values("__sort_key__").drop(columns=["__sort_key__"])
        except Exception:
            trend = trend.sort_values(time_label_col)

        return trend, time_label_col, amount_col

    def _configure_trend_axes(
        self,
        fig: Figure,
        ax: Axes,
        trend_data: pd.DataFrame,
        time_col: str,
        font_prop: Any,
    ) -> None:
        """
        Configure axes for trend line chart with readable labels.

        Args:
            fig: Matplotlib figure
            ax: Matplotlib axes
            trend_data: Prepared trend data
            time_col: Name of time column
            font_prop: Font properties to apply

        """
        # X ticks and labels
        x_positions = list(range(len(trend_data)))
        labels = [str(v) for v in trend_data[time_col].tolist()]

        # Limit number of ticks for readability
        max_ticks = 12
        if len(x_positions) > max_ticks:
            step = max(1, len(x_positions) // max_ticks)
            sel_positions = list(range(0, len(x_positions), step))
            ax.set_xticks(sel_positions)
            ax.set_xticklabels([labels[i] for i in sel_positions], rotation=45)
        else:
            ax.set_xticks(x_positions)
            ax.set_xticklabels(labels, rotation=45)

        # Y grid and layout
        ax.grid(True, alpha=0.3, axis="y")

        # Apply font if available
        if font_prop:
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                label.set_fontproperties(font_prop)
