from __future__ import annotations

"""Chart generation module for household budget visualization.

This module provides ChartGenerator class for creating various types of charts
from household data using matplotlib with Japanese font support.
"""

import io
import os
import sys
import warnings
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

import pandas as pd

try:
    import matplotlib
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure
    from matplotlib.text import Text
    from matplotlib.ticker import FuncFormatter

    HAS_VISUALIZATION_DEPS = True
except ImportError:
    HAS_VISUALIZATION_DEPS = False

from ..exceptions import ChartGenerationError


class ChartGenerator:
    """Chart generator for household budget data visualization.

    This class handles creation of various chart types (pie, bar, line, area)
    with proper Japanese font support and consistent styling.
    """

    def __init__(self, font_path: Optional[str] = None):
        """Initialize chart generator.

        Args:
            font_path: Optional path to Japanese font file.
                      If None, attempts to auto-detect system fonts.
        """
        if not HAS_VISUALIZATION_DEPS:
            raise ChartGenerationError(
                "Visualization dependencies not installed. "
                "Install with: pip install household-mcp-server[visualization]"
            )

        self.font_path = font_path or self._detect_japanese_font()
        self._setup_matplotlib()

    def _setup_matplotlib(self) -> None:
        """Setup matplotlib configuration for Japanese text rendering."""
        # Use non-interactive backend for server environment
        matplotlib.use("Agg")

        # Configure font
        if self.font_path:
            try:
                # Register the font
                font_prop = fm.FontProperties(fname=self.font_path)
                font_name = font_prop.get_name()

                # Set as default font (family and sans-serif)
                plt.rcParams["font.family"] = font_name
                plt.rcParams["font.sans-serif"] = [
                    font_name,
                    "Noto Sans CJK JP",
                    "Noto Sans CJK",
                    "IPAPGothic",
                    "Yu Gothic",
                    "Meiryo",
                    "MS Gothic",
                    "DejaVu Sans",
                ]
            except (OSError, RuntimeError, ValueError):
                # Fallback to system default
                pass

        # グローバルな警告フィルタは副作用を引き起こすため削除
        # 各チャート生成メソッド内で必要に応じてwarnings.catch_warnings()を利用します

        # Configure general plot settings
        plt.rcParams.update(
            {
                "font.size": 12,
                "axes.titlesize": 16,
                "axes.labelsize": 14,
                "axes.titleweight": "bold",
                "figure.figsize": (10, 6),
                "figure.dpi": 100,
                "savefig.dpi": 150,
                "savefig.bbox": "tight",
                "savefig.facecolor": "white",
                "axes.facecolor": "white",
                "axes.edgecolor": "black",
                "axes.linewidth": 1.0,
                "grid.alpha": 0.3,
            }
        )

    def create_monthly_pie_chart(
        self, data: pd.DataFrame, title: str = "月次支出構成", **options: Any
    ) -> io.BytesIO:
        """Create pie chart for monthly expense breakdown.

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
                        "Japanese font not found. Text may not render correctly. "
                        "Install a CJK font (e.g., 'Noto Sans CJK JP').",
                        UserWarning,
                        stacklevel=2,
                    )
                colors = self._get_colors(len(chart_data))

                pie_result = ax.pie(
                    chart_data["amount"],
                    labels=chart_data["category"],
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
            raise ChartGenerationError(f"Failed to create pie chart: {str(e)}") from e

    def create_category_trend_line(
        self,
        data: pd.DataFrame,
        category: Optional[str] = None,
        title: Optional[str] = None,
        **options: Any,
    ) -> io.BytesIO:
        """Create line chart for category trend over time.

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
                trend_data, time_col, amount_col = self._prepare_trend_line_data(data)

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
                        "Japanese font not found. Text may not render correctly. "
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
            raise ChartGenerationError(f"Failed to create line chart: {str(e)}") from e

    def _detect_japanese_font(self) -> Optional[str]:
        """Auto-detect Japanese font available on the system.

        Returns:
            Path to detected Japanese font, or None if not found.
        """
        # First try local fonts directory
        local_font = self._check_local_fonts_dir()
        if local_font:
            return local_font

        # Then try platform-specific font paths
        font_path = self._get_platform_font_candidates()
        if font_path:
            return font_path

        # Then try matplotlib font manager
        return self._find_font_via_matplotlib()

    def _check_local_fonts_dir(self) -> Optional[str]:
        """Check for fonts in local fonts/ directory.

        Returns:
            Path to font file in fonts/ directory, or None if not found.
        """
        # Get project root (assuming we're in src/household_mcp/visualization/)
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        fonts_dir = project_root / "fonts"

        if not fonts_dir.exists():
            return None

        # Check for common Japanese font files
        font_candidates = [
            "NotoSansCJK-Regular.ttc",
            "NotoSansCJKjp-Regular.ttc",
            "NotoSansCJK-Regular.otf",
            "NotoSansCJKjp-Regular.otf",
            "NotoSansCJK-Regular.ttf",
        ]

        for font_name in font_candidates:
            font_path = fonts_dir / font_name
            if font_path.exists():
                return str(font_path)

        return None

    def _get_platform_font_candidates(self) -> Optional[str]:
        """Get platform-specific font candidates and check existence."""
        font_candidates = []

        if sys.platform.startswith("linux"):
            font_candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.otf",
                "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
                "/usr/share/fonts/truetype/noto/NotoSansCJKjp-Regular.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJKjp-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.ttc",
            ]
        elif sys.platform == "darwin":  # macOS
            font_candidates = [
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Unicode MS.ttf",
            ]
        elif sys.platform.startswith("win"):  # Windows
            font_candidates = [
                "C:/Windows/Fonts/msgothic.ttc",
                "C:/Windows/Fonts/meiryo.ttc",
                "C:/Windows/Fonts/YuGothM.ttc",
            ]

        for font_path in font_candidates:
            if os.path.exists(font_path):
                return font_path

        return None

    def _find_font_via_matplotlib(self) -> Optional[str]:
        """Find Japanese font using matplotlib font manager."""
        try:
            japanese_font_names = [
                "Noto Sans CJK JP",
                "Hiragino Sans",
                "MS Gothic",
                "Meiryo",
                "Yu Gothic",
                "DejaVu Sans",
            ]

            for font_name in japanese_font_names:
                try:
                    font_prop = fm.FontProperties(family=font_name)
                    font_file = fm.findfont(font_prop)
                    if font_file and os.path.exists(font_file):
                        # Explicitly cast to str to satisfy mypy
                        return str(font_file)
                except (ValueError, OSError, RuntimeError):
                    # Try next candidate if this family cannot be resolved
                    continue
        except Exception as e:
            # Unexpected environment error occurred while probing fonts
            warnings.warn(f"Font detection via matplotlib failed: {e}", UserWarning)

        return None

    def create_comparison_bar_chart(
        self, data: pd.DataFrame, title: str = "カテゴリ別比較", **options: Any
    ) -> io.BytesIO:
        """Create bar chart for category comparison."""
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
                category_col, amount_col = self._infer_category_amount_columns(
                    chart_data
                )
                font_prop = self._get_font_properties()
                if font_prop is None and self.font_path is None:
                    warnings.warn(
                        "Japanese font not found. Text may not render correctly. "
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
                    chart_data[category_col], chart_data[amount_col], color=colors
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
            raise ChartGenerationError(f"Failed to create bar chart: {str(e)}") from e

    def _parse_image_size(self, size_str: str) -> Tuple[int, int]:
        """Parse image size string to width, height tuple.

        Args:
            size_str: Size string like "800x600"

        Returns:
            Tuple of (width, height)
        """
        try:
            width_str, height_str = size_str.split("x")
            width = int(width_str)
            height = int(height_str)

            # Validate reasonable limits
            if width < 100 or width > 2000 or height < 100 or height > 2000:
                raise ValueError("Size out of reasonable range")

            return width, height
        except Exception:
            # Return default size
            return 800, 600

    def _get_colors(self, n_colors: int) -> List[str]:
        """Get a list of colors for charts.

        Args:
            n_colors: Number of colors needed

        Returns:
            List of color strings
        """
        # Default color palette optimized for visibility
        default_colors = [
            "#FF6B6B",  # Red
            "#4ECDC4",  # Teal
            "#45B7D1",  # Blue
            "#96CEB4",  # Green
            "#FFEAA7",  # Yellow
            "#DDA0DD",  # Plum
            "#98D8C8",  # Mint
            "#F7DC6F",  # Light Yellow
            "#BB8FCE",  # Light Purple
            "#85C1E9",  # Light Blue
        ]

        # Repeat colors if needed
        colors = []
        for i in range(n_colors):
            colors.append(default_colors[i % len(default_colors)])

        return colors

    def _prepare_pie_chart_data(self, data: pd.DataFrame) -> pd.DataFrame:
        if {"category", "amount"}.issubset(data.columns):
            chart_data = data[["category", "amount"]].copy()
        else:
            amount_col = self._infer_column(data.columns, ["金額", "amount", "円"])
            category_col = self._infer_column(
                data.columns, ["カテゴリ", "category", "項目", "大項目"]
            )
            if not amount_col or not category_col:
                raise ChartGenerationError(
                    "Cannot identify category and amount columns"
                )
            chart_data = data[[category_col, amount_col]].copy()
            chart_data.columns = ["category", "amount"]

        chart_data = chart_data[chart_data["amount"] > 0]
        chart_data = chart_data.groupby("category", as_index=False)["amount"].sum()
        chart_data = chart_data.sort_values("amount", ascending=False)

        if chart_data.empty:
            raise ChartGenerationError("No positive amounts found for pie chart")

        return chart_data

    def _infer_column(self, columns: List[str], keywords: List[str]) -> Optional[str]:
        for col in columns:
            lower_col = str(col).lower()
            if any(keyword in lower_col for keyword in keywords):
                return col
        return None

    def _infer_category_amount_columns(self, df: pd.DataFrame) -> Tuple[str, str]:
        """Infer (category_col, amount_col) from DataFrame columns."""
        category_col = self._infer_column(
            list(df.columns), ["カテゴリ", "category", "項目", "大項目"]
        )
        amount_col = self._infer_column(list(df.columns), ["金額", "amount", "円"])
        if not category_col or not amount_col:
            raise ChartGenerationError("Cannot identify category and amount columns")
        return category_col, amount_col

    def _render_bar_value_labels(
        self, ax: Axes, bars: Sequence[Any], font_prop: Optional[fm.FontProperties]
    ) -> None:
        """Render value labels at the end of horizontal bars."""
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
        """Apply thousands separator + 円 unit to X axis."""
        ax.xaxis.set_major_formatter(FuncFormatter(lambda x, p: f"{int(x):,}円"))

    def _get_font_properties(self) -> Optional[fm.FontProperties]:
        """Create FontProperties from configured font_path if available."""
        if not self.font_path:
            return None
        try:
            return fm.FontProperties(fname=self.font_path)
        except Exception:
            return None

    def _style_pie_labels(
        self,
        texts: List[Text],
        autotexts: List[Text],
        font_prop: Optional[fm.FontProperties],
    ) -> None:
        """Apply styling to pie chart labels and autopct texts."""
        for autotext in autotexts:
            autotext.set_color("white")
            autotext.set_fontweight("bold")
            if font_prop:
                autotext.set_fontproperties(font_prop)
        for text in texts:
            if font_prop:
                text.set_fontproperties(font_prop)

    def _save_figure_to_buffer(self, fig: Figure) -> io.BytesIO:
        """Save the figure to a BytesIO buffer as PNG and return it."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        buffer.seek(0)
        plt.close(fig)
        return buffer

    def _create_figure(self, size_str: str) -> Tuple[Figure, Axes]:
        """Create a matplotlib figure/axes with the given pixel size string."""
        width, height = self._parse_image_size(size_str)
        fig, ax = plt.subplots(figsize=(width / 100, height / 100))
        return fig, ax

    def _prepare_trend_line_data(
        self, data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, str, str]:
        """Prepare data for trend line plotting.

        Returns a tuple of (trend_data, time_col, amount_col).
        """
        # Infer columns
        time_col = self._infer_column(
            list(data.columns), ["month", "date", "年月", "月", "期間"]
        )
        amount_col = self._infer_column(list(data.columns), ["金額", "amount", "円"])
        if not time_col or not amount_col:
            raise ChartGenerationError("Cannot identify time and amount columns")

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
        font_prop: Optional[fm.FontProperties],
    ) -> None:
        """Configure axes for trend line chart with readable labels."""
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
