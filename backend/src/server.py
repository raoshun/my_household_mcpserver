"""
FastMCP server entry point for household budget analysis.

This module serves as the main entry point for the FastMCP server implementation,
providing household budget analysis capabilities through MCP protocol.
It handles command-line arguments and initializes the server with appropriate
transport configurations.
"""

import argparse
import warnings
from typing import Any

from fastmcp import FastMCP

from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.tools import category_trend_summary, get_category_trend

# Suppress third-party deprecation warnings at runtime
warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    module="dateutil.*",
)
warnings.filterwarnings(
    "ignore",
    message="datetime.datetime.utcfromtimestamp.*is deprecated",
    category=DeprecationWarning,
)

# コマンドライン引数で transport を受け取る
parser = argparse.ArgumentParser()
parser.add_argument(
    "--transport",
    nargs="+",
    default=["stdio"],
    help="Transport(s) for MCP server",
)
parser.add_argument("--host", default="localhost")
parser.add_argument("--port", type=int, default=8000)
args, unknown = parser.parse_known_args()

mcp = FastMCP("my_household_mcp")
data_loader = HouseholdDataLoader(src_dir="data")

# transportにstreamable-httpが含まれる場合はmime_typeをtext/event-streamに
is_streamable = "streamable-http" in args.transport


@mcp.resource(
    "data://category_hierarchy",
    mime_type="text/event-stream" if is_streamable else None,
)
def get_category_hierarchy() -> dict[str, list[str]]:
    """
    家計簿のカテゴリの階層構造を取得する関数。

    Returns:
        dict[str, list[str]]: カテゴリの階層構造(大項目: [中項目1, 中項目2, ...])を表す辞書

    """
    result = data_loader.category_hierarchy(year=2025, month=7)
    return dict(result)  # 明示的キャスト


# 家計簿から指定した年月の収支を取得するツール


@mcp.tool(
    "get_monthly_household",
)
def get_monthly_household(year: int, month: int) -> list[dict[str, Any]]:
    """
    指定した年月の家計簿から収支を取得する関数。

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list[dict]: 支出のリスト

    """
    df = data_loader.load_month(year, month)
    return [dict(record) for record in df.to_dict(orient="records")]


@mcp.resource(
    "data://available_months", mime_type="text/event-stream" if is_streamable else None
)
def get_available_months() -> list[dict[str, int]]:
    """利用可能な月のリストを CSV ファイルから動的に検出して返す。"""

    months = list(data_loader.iter_available_months())
    return [{"year": year, "month": month} for year, month in months]


@mcp.resource(
    "data://household_categories",
    mime_type="text/event-stream" if is_streamable else None,
)
def get_household_categories() -> dict[str, list[str]]:
    """
    家計簿のカテゴリ一覧を取得する関数。

    Returns:
        dict[str, list[str]]: カテゴリの階層構造(大項目: [中項目1, 中項目2, ...])を表す辞書

    """
    result = data_loader.category_hierarchy(year=2025, month=7)
    return dict(result)  # 明示的キャスト


@mcp.resource(
    "data://category_trend_summary",
    mime_type="text/event-stream" if is_streamable else None,
)
def get_category_trend_summary() -> dict[str, Any]:
    """トレンド分析用のカテゴリ集計結果を返す。"""

    result = category_trend_summary(src_dir="data")
    return dict(result)  # 明示的キャスト


@mcp.tool("get_category_trend")
def run_get_category_trend(
    category: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
) -> dict[str, Any]:
    """カテゴリ別の支出トレンドを取得する MCP ツール。"""

    result = get_category_trend(
        category=category,
        start_month=start_month,
        end_month=end_month,
        src_dir="data",
    )
    return dict(result)  # 明示的キャスト


# 実行処理
if __name__ == "__main__":
    # transportはリスト型なので、最初の要素のみ渡す
    transport = args.transport[0]
    if transport == "stdio":
        mcp.run(transport=transport)
    else:
        mcp.run(transport=transport, host=args.host, port=args.port)
