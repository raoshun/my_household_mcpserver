"""REST API routes"""

from .assets import router as assets_router
from .chart_routes import create_chart_router
from .core_routes import create_core_router
from .financial_independence import router as fi_router
from .monthly_routes import create_monthly_router
from .transactions import router as transactions_router

__all__ = [
    "assets_router",
    "create_chart_router",
    "create_core_router",
    "create_monthly_router",
    "fi_router",
    "transactions_router",
]
