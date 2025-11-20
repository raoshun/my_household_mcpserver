"""Base chart generator with common functionality."""

from __future__ import annotations

import io
import os
import sys
import warnings
from pathlib import Path

try:
    import matplotlib
    import matplotlib.font_manager as fm
    import matplotlib.pyplot as plt
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    HAS_VISUALIZATION_DEPS = True
except ImportError:
    HAS_VISUALIZATION_DEPS = False

from ..exceptions import ChartGenerationError


class BaseChartGenerator:
    """Base class for chart generators with common functionality."""

    def __init__(self, font_path: str | None = None):
        """
        Initialize base chart generator.

        Args:
            font_path: Optional path to Japanese font file.
                      If None, attempts to auto-detect system fonts.

        """
        if not HAS_VISUALIZATION_DEPS:
            raise ChartGenerationError(
                "Visualization dependencies not installed. "
                "Install with: pip install household-mcp-server[visualization]"
            )

        # Validate font_path if provided
        if font_path and not os.path.exists(font_path):
            warnings.warn(
                f"Font path '{font_path}' does not exist. Will attempt auto-detection.",
                UserWarning,
                stacklevel=2,
            )
            font_path = None

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

    def _detect_japanese_font(self) -> str | None:
        """
        Auto-detect Japanese font available on the system.

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

    def _check_local_fonts_dir(self) -> str | None:
        """
        Check for fonts in local fonts/ directory.

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

    def _get_platform_font_candidates(self) -> str | None:
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

    def _find_font_via_matplotlib(self) -> str | None:
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
                        return str(font_file)
                except (ValueError, OSError, RuntimeError):
                    continue
        except Exception as e:
            warnings.warn(
                f"Font detection via matplotlib failed: {e}",
                UserWarning,
                stacklevel=2,
            )

        return None

    def _parse_image_size(self, size_str: str) -> tuple[int, int]:
        """
        Parse image size string to width, height tuple.

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

    def _get_colors(self, n_colors: int) -> list[str]:
        """
        Get a list of colors for charts.

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

    def _get_font_properties(self) -> fm.FontProperties | None:
        """Create FontProperties from configured font_path if available."""
        if not self.font_path:
            return None
        try:
            return fm.FontProperties(fname=self.font_path)
        except Exception:
            return None

    def _save_figure_to_buffer(self, fig: Figure) -> io.BytesIO:
        """Save the figure to a BytesIO buffer as PNG and return it."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        buffer.seek(0)
        plt.close(fig)
        return buffer

    def _create_figure(self, size_str: str) -> tuple[Figure, Axes]:
        """Create a matplotlib figure/axes with the given pixel size string."""
        width, height = self._parse_image_size(size_str)
        fig, ax = plt.subplots(figsize=(width / 100, height / 100))
        return fig, ax

    def _infer_column(self, columns: list[str], keywords: list[str]) -> str | None:
        """Infer column name from DataFrame columns using keywords."""
        for col in columns:
            lower_col = str(col).lower()
            if any(keyword in lower_col for keyword in keywords):
                return col
        return None
