"""REST API routes"""

from .assets import router as assets_router
from .financial_independence import router as fi_router
from .transactions import router as transactions_router

__all__ = ["assets_router", "fi_router", "transactions_router"]
