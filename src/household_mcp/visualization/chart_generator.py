"""Chart generation module for household budget visualization.

This module provides ChartGenerator class for creating various types of charts
from household data using matplotlib with Japanese font support.
"""

import io
import os
import sys
from typing import List, Optional, Tuple

import pandas as pd

try:
    import matplotlib
    import matplotlib.pyplot as plt
    import matplotlib.font_manager as fm
    
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
    
    def _detect_japanese_font(self) -> Optional[str]:
        """Auto-detect Japanese font available on the system.
        
        Returns:
            Path to detected Japanese font, or None if not found.
        """
        # First try platform-specific font paths
        font_path = self._get_platform_font_candidates()
        if font_path:
            return font_path
        
        # Then try matplotlib font manager
        return self._find_font_via_matplotlib()
    
    def _get_platform_font_candidates(self) -> Optional[str]:
        """Get platform-specific font candidates and check existence."""
        font_candidates = []
        
        if sys.platform.startswith('linux'):
            font_candidates = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            ]
        elif sys.platform == 'darwin':  # macOS
            font_candidates = [
                "/System/Library/Fonts/Hiragino Sans GB.ttc",
                "/Library/Fonts/Arial Unicode MS.ttf",
            ]
        elif sys.platform.startswith('win'):  # Windows
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
                'Noto Sans CJK JP', 'Hiragino Sans', 'MS Gothic',
                'Meiryo', 'Yu Gothic', 'DejaVu Sans'
            ]
            
            for font_name in japanese_font_names:
                try:
                    font_prop = fm.FontProperties(family=font_name)
                    font_file = fm.findfont(font_prop)
                    if font_file and os.path.exists(font_file):
                        return font_file
                except Exception:
                    continue
        except Exception:
            pass
        
        return None
    
    def _setup_matplotlib(self) -> None:
        """Setup matplotlib configuration for Japanese text rendering."""
        # Use non-interactive backend for server environment
        matplotlib.use('Agg')
        
        # Configure font
        if self.font_path:
            try:
                # Register the font
                font_prop = fm.FontProperties(fname=self.font_path)
                font_name = font_prop.get_name()
                
                # Set as default font
                plt.rcParams['font.family'] = font_name
            except Exception:
                # Fallback to system default
                pass
        
        # Configure general plot settings
        plt.rcParams.update({
            'font.size': 12,
            'axes.titlesize': 16,
            'axes.labelsize': 14,
            'axes.titleweight': 'bold',
            'figure.figsize': (10, 6),
            'figure.dpi': 100,
            'savefig.dpi': 150,
            'savefig.bbox': 'tight',
            'savefig.facecolor': 'white',
            'axes.facecolor': 'white',
            'axes.edgecolor': 'black',
            'axes.linewidth': 1.0,
            'grid.alpha': 0.3,
        })
    
    def create_monthly_pie_chart(
        self,
        data: pd.DataFrame,
        title: str = "月次支出構成",
        **options
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
            # Parse image size
            width, height = self._parse_image_size(options.get('image_size', '800x600'))
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width/100, height/100))
            
            # Prepare data - ensure we have category and amount columns
            if 'category' not in data.columns or 'amount' not in data.columns:
                # Try to infer columns
                amount_col = None
                category_col = None
                
                for col in data.columns:
                    if any(x in col.lower() for x in ['金額', 'amount', '円']):
                        amount_col = col
                    elif any(x in col.lower() for x in ['カテゴリ', 'category', '項目', '大項目']):
                        category_col = col
                
                if not amount_col or not category_col:
                    raise ChartGenerationError("Cannot identify category and amount columns")
                
                chart_data = data[[category_col, amount_col]].copy()
                chart_data.columns = ['category', 'amount']
            else:
                chart_data = data[['category', 'amount']].copy()
            
            # Filter positive amounts and group by category
            chart_data = chart_data[chart_data['amount'] > 0]
            chart_data = chart_data.groupby('category')['amount'].sum().reset_index()
            chart_data = chart_data.sort_values('amount', ascending=False)
            
            if chart_data.empty:
                raise ChartGenerationError("No positive amounts found for pie chart")
            
            # Create pie chart
            colors = self._get_colors(len(chart_data))
            wedges, texts, autotexts = ax.pie(
                chart_data['amount'],
                labels=chart_data['category'],
                colors=colors,
                autopct='%1.1f%%',
                startangle=90,
                counterclock=False
            )
            
            # Styling
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_weight('bold')
            
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            
            # Equal aspect ratio ensures that pie is drawn as a circle
            ax.axis('equal')
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            
            plt.close(fig)
            return buffer
            
        except Exception as e:
            plt.close('all')  # Clean up any open figures
            raise ChartGenerationError(f"Failed to create pie chart: {str(e)}")
    
    def create_category_trend_line(
        self, 
        data: pd.DataFrame,
        category: Optional[str] = None,
        title: Optional[str] = None,
        **options
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
            # Parse image size
            width, height = self._parse_image_size(options.get('image_size', '800x600'))
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width/100, height/100))
            
            # Prepare data
            trend_data = data.copy()
            
            # Ensure we have time and amount columns
            time_col = None
            amount_col = None
            
            for col in trend_data.columns:
                if any(x in col.lower() for x in ['date', '日付', 'month', '月', 'time']):
                    time_col = col
                elif any(x in col.lower() for x in ['金額', 'amount', '円']):
                    amount_col = col
            
            if not time_col or not amount_col:
                raise ChartGenerationError("Cannot identify time and amount columns")
            
            # Sort by time
            trend_data = trend_data.sort_values(time_col)
            
            # Create line plot
            ax.plot(
                range(len(trend_data)), 
                trend_data[amount_col],
                marker='o',
                linewidth=2,
                markersize=6,
                color='#1f77b4'
            )
            
            # Set x-axis labels
            ax.set_xticks(range(len(trend_data)))
            ax.set_xticklabels(trend_data[time_col], rotation=45)
            
            # Set title
            if not title:
                title = f"{category or 'カテゴリ'}の推移" if category else "支出推移"
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            
            # Set labels
            ax.set_xlabel('期間', fontsize=12)
            ax.set_ylabel('金額 (円)', fontsize=12)
            
            # Add grid
            ax.grid(True, alpha=0.3)
            
            # Format y-axis to show currency
            ax.yaxis.set_major_formatter(plt.FuncFormatter(
                lambda x, p: f'{int(x):,}円'
            ))
            
            plt.tight_layout()
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            
            plt.close(fig)
            return buffer
            
        except Exception as e:
            plt.close('all')
            raise ChartGenerationError(f"Failed to create line chart: {str(e)}")
    
    def create_comparison_bar_chart(
        self,
        data: pd.DataFrame,
        title: str = "カテゴリ別比較",
        **options
    ) -> io.BytesIO:
        """Create bar chart for category comparison.
        
        Args:
            data: DataFrame with categories and amounts
            title: Chart title
            **options: Additional chart options
            
        Returns:
            BytesIO buffer containing the chart image
        """
        try:
            # Parse image size
            width, height = self._parse_image_size(options.get('image_size', '800x600'))
            
            # Create figure
            fig, ax = plt.subplots(figsize=(width/100, height/100))
            
            # Prepare data
            chart_data = data.copy()
            
            # Identify columns
            category_col = None
            amount_col = None
            
            for col in chart_data.columns:
                if any(x in col.lower() for x in ['カテゴリ', 'category', '項目']):
                    category_col = col
                elif any(x in col.lower() for x in ['金額', 'amount', '円']):
                    amount_col = col
            
            if not category_col or not amount_col:
                raise ChartGenerationError("Cannot identify category and amount columns")
            
            # Group and sort
            chart_data = chart_data.groupby(category_col)[amount_col].sum().reset_index()
            chart_data = chart_data.sort_values(amount_col, ascending=True)  # Ascending for horizontal bar
            
            # Create horizontal bar chart
            colors = self._get_colors(len(chart_data))
            bars = ax.barh(
                chart_data[category_col],
                chart_data[amount_col],
                color=colors
            )
            
            # Add value labels on bars
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2, 
                       f'{int(width):,}円',
                       ha='left', va='center', fontweight='bold')
            
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
            ax.set_xlabel('金額 (円)', fontsize=12)
            
            # Format x-axis
            ax.xaxis.set_major_formatter(plt.FuncFormatter(
                lambda x, p: f'{int(x):,}円'
            ))
            
            ax.grid(True, alpha=0.3, axis='x')
            
            plt.tight_layout()
            
            # Save to buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            
            plt.close(fig)
            return buffer
            
        except Exception as e:
            plt.close('all')
            raise ChartGenerationError(f"Failed to create bar chart: {str(e)}")
    
    def _parse_image_size(self, size_str: str) -> Tuple[int, int]:
        """Parse image size string to width, height tuple.
        
        Args:
            size_str: Size string like "800x600"
            
        Returns:
            Tuple of (width, height)
        """
        try:
            width_str, height_str = size_str.split('x')
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
            '#FF6B6B',  # Red
            '#4ECDC4',  # Teal
            '#45B7D1',  # Blue
            '#96CEB4',  # Green
            '#FFEAA7',  # Yellow
            '#DDA0DD',  # Plum
            '#98D8C8',  # Mint
            '#F7DC6F',  # Light Yellow
            '#BB8FCE',  # Light Purple
            '#85C1E9',  # Light Blue
        ]
        
        # Repeat colors if needed
        colors = []
        for i in range(n_colors):
            colors.append(default_colors[i % len(default_colors)])
        
        return colors