from typing import Union
from fastmcp import FastMCP, Context

from household_mcp.dataloader import (
    iter_available_months,
    load_csv_from_month,
)

# サーバを初期化
mcp = FastMCP("my_household_mcp")

# 家計簿のカテゴリの階層構造を取得するリソース


@mcp.resource("data://category_hierarchy")
def get_category_hierarchy() -> dict[str, list[str]]:
    """
    家計簿のカテゴリの階層構造を取得する関数。

    Returns:
        dict[str, list[str]]: カテゴリの階層構造(大項目: [中項目1, 中項目2, ...])を表す辞書
    """
    # データディレクトリから対象月のCSVを読み込む
    df = load_csv_from_month(year=2025, month=7, src_dir="data")

    groups: dict[str, list[str]] = {}
    for name, group in df.groupby("大項目"):
        mids = sorted(group["中項目"].dropna().astype(str).unique())
        groups[str(name)] = mids
    return groups

# 家計簿から指定した年月の収支を取得するツール


@mcp.tool("get_monthly_household")
def get_monthly_household(year: int, month: int) -> list[dict]:
    """
    指定した年月の家計簿から収支を取得する関数。

    Args:
        year (int): 年
        month (int): 月

    Returns:
        list[dict]: 支出のリスト
    """
    df = load_csv_from_month(year, month, src_dir="data")
    return df.to_dict(orient="records")


@mcp.resource("data://available_months")
def get_available_months() -> list[dict[str, int]]:
    """利用可能な月のリストを CSV ファイルから動的に検出して返す。"""

    months = list(iter_available_months(src_dir="data"))
    return [{"year": year, "month": month} for year, month in months]


@mcp.resource("data://household_categories")
def get_household_categories() -> dict[str, list[str]]:
    """
    家計簿のカテゴリ一覧を取得する関数。

    Returns:
        dict[str, list[str]]: カテゴリの階層構造(大項目: [中項目1, 中項目2, ...])を表す辞書
    """
    # データディレクトリから対象月のCSVを読み込む
    df = load_csv_from_month(year=2025, month=7, src_dir="data")

    groups: dict[str, list[str]] = {}
    for name, group in df.groupby("大項目"):
        mids = sorted(group["中項目"].dropna().astype(str).unique())
        groups[str(name)] = mids
    return groups


# 実行処理
if __name__ == "__main__":
    mcp.run(transport="stdio")
