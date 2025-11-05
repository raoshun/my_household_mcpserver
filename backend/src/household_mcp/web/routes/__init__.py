"""REST API routes"""

from .financial_independence import router as fi_router

__all__ = ["fi_router"]
