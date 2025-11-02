"""
Chart styling and color configuration for household budget visualization.

This module provides consistent styling, color palettes, and matplotlib
configuration for all chart types in the household MCP server.
"""


class ChartStyles:
    """Chart styling configuration and color palettes."""

    # Default color palette optimized for visibility and accessibility
    DEFAULT_COLORS = [
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
        "#F8C471",  # Orange
        "#A9DFBF",  # Light Green
    ]

    # Category-specific colors for common household categories
    CATEGORY_COLORS = {
        "食費": "#FF6B6B",
        "住居費": "#4ECDC4",
        "光熱費": "#45B7D1",
        "通信費": "#96CEB4",
        "交通費": "#FFEAA7",
        "医療費": "#DDA0DD",
        "教育費": "#98D8C8",
        "娯楽費": "#F7DC6F",
        "被服費": "#BB8FCE",
        "日用品": "#85C1E9",
        "保険料": "#F8C471",
        "その他": "#A9DFBF",
    }

    # matplotlib rcParams for consistent styling
    RCPARAMS = {
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
        "grid.color": "#CCCCCC",
        "axes.spines.top": False,
        "axes.spines.right": False,
    }

    @classmethod
    def get_colors(cls, categories: list[str]) -> list[str]:
        """
        Get colors for a list of categories.

        Args:
            categories: List of category names

        Returns:
            List of color strings matching the categories

        """
        colors = []
        for i, category in enumerate(categories):
            # First try category-specific colors
            if category in cls.CATEGORY_COLORS:
                colors.append(cls.CATEGORY_COLORS[category])
            else:
                # Fallback to default palette
                colors.append(cls.DEFAULT_COLORS[i % len(cls.DEFAULT_COLORS)])

        return colors

    @classmethod
    def get_default_colors(cls, n_colors: int) -> list[str]:
        """
        Get n colors from the default palette.

        Args:
            n_colors: Number of colors needed

        Returns:
            List of color strings

        """
        colors = []
        for i in range(n_colors):
            colors.append(cls.DEFAULT_COLORS[i % len(cls.DEFAULT_COLORS)])
        return colors

    @classmethod
    def get_single_color(cls, category: str) -> str:
        """
        Get color for a single category.

        Args:
            category: Category name

        Returns:
            Color string

        """
        return cls.CATEGORY_COLORS.get(category, cls.DEFAULT_COLORS[0])
