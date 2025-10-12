"""Household MCP Server implementation.

This module provides an MCP server for household budget analysis with FastAPI integration.
It includes tools for analyzing budget data from CSV files and provides natural language
interface for financial data queries.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Sequence

import pandas as pd
from fastapi import FastAPI
from mcp.server import Server
from mcp.types import Tool

# from src.household_mcp.dataloader import load_csv_from_month

# サーバーインスタンスの作成
server = Server("household-mcp")

# データファイルのパス
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

# MoneyForwardのCSV列名マッピング
COLUMNS_MAP = {
    0: "calc_target",
    1: "date",
    2: "description",
    3: "amount",
    4: "institution",
    5: "major_category",
    6: "minor_category",
    7: "memo",
    8: "transfer",
    9: "id",
}


class BudgetAnalyzer:
    """Analyzes budget data from a CSV file."""

    def __init__(self, csv_path: Path, encoding: str = "shift_jis"):
        """Initializes the BudgetAnalyzer with the specified CSV file path and encoding.

        Args:
            csv_path (Path): Path to the CSV file containing budget data.
            encoding (str, optional): Encoding of the CSV file. Defaults to "shift_jis".
        """
        self.csv_path = csv_path
        self.encoding = encoding
        self.df = pd.DataFrame(columns=list(COLUMNS_MAP.values()))

    def load_data(self) -> None:
        """Loads budget data from the CSV file."""
        try:
            self.df = pd.read_csv(self.csv_path, encoding=self.encoding)
            # 列名の標準化
            if len(self.df.columns) >= 10:
                self.df.columns = list(COLUMNS_MAP.values())

            # データ型の変換
            self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
            self.df["amount"] = pd.to_numeric(self.df["amount"], errors="coerce")
            self.df["calc_target"] = pd.to_numeric(
                self.df["calc_target"], errors="coerce"
            )

            print(f"データ読み込み完了: {len(self.df)}件のレコード")

        except (FileNotFoundError, pd.errors.ParserError, UnicodeDecodeError) as e:
            print(f"データ読み込みエラー: {e}")
            self.df = pd.DataFrame(columns=list(COLUMNS_MAP.values()))

    def get_monthly_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Returns a summary of the monthly budget data for the specified year and
        month."""
        if self.df.empty:
            return {"message": "No data available."}

        # 指定月のデータを抽出
        mask = (self.df["date"].dt.year == year) & (self.df["date"].dt.month == month)
        monthly_data = self.df[mask]

        if monthly_data.empty:
            return {"message": f"No data for {year}-{month:02d}."}

        # 収入と支出の集計
        income_data = monthly_data[monthly_data["amount"] > 0]
        expense_data = monthly_data[monthly_data["amount"] < 0]

        total_income = income_data["amount"].sum()
        total_expense = abs(expense_data["amount"].sum())

        balance = total_income - total_expense

        # 月ごとのカテゴリ別集計
        category_summary = (
            expense_data.groupby("minor_category")["amount"]
            .sum()
            .abs()
            .sort_values(ascending=False)
        )

        # 結果のまとめ
        summary = {
            "period": f"{year}-{month:02d}",
            "total_income": int(total_income),
            "total_expense": int(total_expense),
            "balance": int(balance),
            "expense_by_category": category_summary.to_dict(),
            "transaction_count": len(monthly_data),
        }

        return summary


# グローバルインスタンス
analyzer: Optional[BudgetAnalyzer] = None


# mcp Server のデコレータが未型定義のため、mypy の誤検知を抑制
@server.list_tools()  # type: ignore[misc,no-untyped-call]
async def list_tools() -> Sequence[Tool]:
    """Lists available tools for the server."""

    return [
        Tool(
            name="monthly_summary",
            description="Get monthly budget summary for a specific year and month.",
            inputSchema={
                "type": "object",
                "properties": {
                    "year": {
                        "type": "integer",
                        "description": "Year of the budget data.",
                    },
                    "month": {
                        "type": "integer",
                        "description": "Month of the budget data.",
                    },
                },
                "required": ["year", "month"],
            },
        ),
        Tool(
            name="category_analysis",
            description="Analyze expenses by category for a specific year and month.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Minor category of expenses to analyze.",
                    },
                    "months": {
                        "type": "int",
                        "description": "Number of months to analyze from the current month.(default: 3)",
                        "default": 3,
                    },
                },
                "required": ["category"],
            },
        ),
        Tool(
            name="find_categories",
            description="Find all unique expense categories.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


# FastAPI/uvicorn用のASGIアプリエクスポート
app = FastAPI()

# 必要に応じてFastAPIルーティング追加（現状は空）

# MCP ServerのASGIラッパー（今後拡張する場合はここで統合）
