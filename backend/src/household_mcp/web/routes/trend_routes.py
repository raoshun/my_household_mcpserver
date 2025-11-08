"""Trend analysis API routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)


def create_trend_router() -> APIRouter:
    """
    Create trend analysis API router.

    Returns:
        APIRouter with trend endpoints

    """
    router = APIRouter(prefix="/api/trend", tags=["trend"])

    @router.get("/monthly_summary")
    async def get_monthly_summary(  # type: ignore[no-untyped-def]
        start_year: int = Query(..., description="Start year"),
        start_month: int = Query(..., ge=1, le=12, description="Start month (1-12)"),
        end_year: int = Query(..., description="End year"),
        end_month: int = Query(..., ge=1, le=12, description="End month (1-12)"),
    ) -> dict[str, Any]:
        """
        Get monthly income/expense summary for a date range.

        Args:
            start_year: Start year of the period
            start_month: Start month of the period (1-12)
            end_year: End year of the period
            end_month: End month of the period (1-12)

        Returns:
            Monthly summary data with income, expense, balance, and cumulative

        """
        try:
            from datetime import date

            from household_mcp.dataloader import HouseholdDataLoader

            # Validate date range
            start_date = date(start_year, start_month, 1)
            end_date = date(end_year, end_month, 1)

            if start_date > end_date:
                raise HTTPException(
                    status_code=400,
                    detail="Start date must be before or equal to end date",
                )

            # Load data for the entire period
            loader = HouseholdDataLoader()
            all_months = []

            current_year = start_year
            current_month = start_month

            while (current_year < end_year) or (
                current_year == end_year and current_month <= end_month
            ):
                all_months.append((current_year, current_month))
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1

            # Aggregate monthly data
            monthly_data = []
            cumulative_balance = 0.0

            for year, month in all_months:
                try:
                    df = loader.load_month(year, month)

                    # Calculate income (positive amounts)
                    income = float(df[df["金額（円）"] > 0]["金額（円）"].sum())

                    # Calculate expense (negative amounts)
                    expense = float(abs(df[df["金額（円）"] < 0]["金額（円）"].sum()))

                    # Balance for the month
                    balance = income - expense
                    cumulative_balance += balance

                    monthly_data.append(
                        {
                            "year": year,
                            "month": month,
                            "year_month": f"{year}-{month:02d}",
                            "income": round(income, 2),
                            "expense": round(expense, 2),
                            "balance": round(balance, 2),
                            "cumulative_balance": round(cumulative_balance, 2),
                            "transaction_count": len(df),
                        }
                    )
                except FileNotFoundError:
                    # Month has no data
                    monthly_data.append(
                        {
                            "year": year,
                            "month": month,
                            "year_month": f"{year}-{month:02d}",
                            "income": 0.0,
                            "expense": 0.0,
                            "balance": 0.0,
                            "cumulative_balance": round(cumulative_balance, 2),
                            "transaction_count": 0,
                        }
                    )

            return {
                "success": True,
                "start_year": start_year,
                "start_month": start_month,
                "end_year": end_year,
                "end_month": end_month,
                "data": monthly_data,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error getting monthly summary: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/category_breakdown")
    async def get_category_breakdown(  # type: ignore[no-untyped-def]
        start_year: int = Query(..., description="Start year"),
        start_month: int = Query(..., ge=1, le=12, description="Start month (1-12)"),
        end_year: int = Query(..., description="End year"),
        end_month: int = Query(..., ge=1, le=12, description="End month (1-12)"),
        top_n: int = Query(5, ge=1, le=20, description="Number of top categories"),
    ) -> dict[str, Any]:
        """
        Get category breakdown trend for a date range.

        Args:
            start_year: Start year of the period
            start_month: Start month of the period (1-12)
            end_year: End year of the period
            end_month: End month of the period (1-12)
            top_n: Number of top categories to return (default: 5)

        Returns:
            Category breakdown data with monthly trends

        """
        try:
            from datetime import date

            import pandas as pd

            from household_mcp.dataloader import HouseholdDataLoader

            # Validate date range
            start_date = date(start_year, start_month, 1)
            end_date = date(end_year, end_month, 1)

            if start_date > end_date:
                raise HTTPException(
                    status_code=400,
                    detail="Start date must be before or equal to end date",
                )

            # Load data for the entire period
            loader = HouseholdDataLoader()
            all_months = []

            current_year = start_year
            current_month = start_month

            while (current_year < end_year) or (
                current_year == end_year and current_month <= end_month
            ):
                all_months.append((current_year, current_month))
                current_month += 1
                if current_month > 12:
                    current_month = 1
                    current_year += 1

            # Load all data and combine
            all_dfs = []
            for year, month in all_months:
                try:
                    df = loader.load_month(year, month)
                    df["year_month"] = f"{year}-{month:02d}"
                    all_dfs.append(df)
                except FileNotFoundError:
                    continue

            if not all_dfs:
                return {
                    "success": True,
                    "start_year": start_year,
                    "start_month": start_month,
                    "end_year": end_year,
                    "end_month": end_month,
                    "categories": [],
                    "months": [],
                    "data": [],
                }

            combined_df = pd.concat(all_dfs, ignore_index=True)

            # Filter expenses only (negative amounts)
            expense_df = combined_df[combined_df["金額（円）"] < 0].copy()
            expense_df["金額（円）"] = expense_df["金額（円）"].abs()  # type: ignore

            # Find top N categories by total expense
            category_totals = (
                expense_df.groupby("大項目")["金額（円）"]
                .sum()
                .sort_values(ascending=False)  # type: ignore
            )
            top_categories = category_totals.head(top_n).index.tolist()

            # Filter to top categories
            top_expense_df = expense_df[
                expense_df["大項目"].isin(top_categories)  # type: ignore
            ]

            # Aggregate by category and month
            category_monthly = (
                top_expense_df.groupby(["大項目", "year_month"])[  # type: ignore
                    "金額（円）"
                ]
                .sum()
                .reset_index()
            )

            # Pivot to get categories as columns
            pivot_data = category_monthly.pivot(
                index="year_month", columns="大項目", values="金額（円）"
            ).fillna(0)

            # Prepare response
            months = sorted(pivot_data.index.tolist())
            categories = top_categories

            # Convert to list of dicts
            data = []
            for month in months:
                month_data: dict[str, Any] = {"year_month": month}
                for category in categories:
                    value = pivot_data.loc[month, category]
                    month_data[str(category)] = round(float(value), 2)
                data.append(month_data)

            return {
                "success": True,
                "start_year": start_year,
                "start_month": start_month,
                "end_year": end_year,
                "end_month": end_month,
                "categories": categories,
                "months": months,
                "data": data,
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error getting category breakdown: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
