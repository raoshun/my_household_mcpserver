"""REST API routes"""

from .financial_independence import router as fi_router
from .transactions import router as transactions_router

__all__ = ["fi_router", "transactions_router"]
