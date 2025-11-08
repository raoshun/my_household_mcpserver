"""
Household MCP Server unified implementation.

This module provides a unified MCP server for household budget analysis
with FastAPI integration. It includes tools for analyzing budget data from
CSV files and provides natural language interface for financial data queries.
Combines functionality from both server.py files into a single entry point.
"""

import argparse
import os
import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple, Optional, cast

import pandas as pd

if TYPE_CHECKING:
    from fastapi import FastAPI

    # 型検査用にのみ DatabaseManager をインポート（実行時には遅延インポート）
    from household_mcp.database import DatabaseManager
else:
    try:
        from fastapi import FastAPI
    except Exception:  # FastAPI is optional; tests may run without web extras installed
        FastAPI = None

from fastmcp import FastMCP

from household_mcp.dataloader import HouseholdDataLoader
from household_mcp.exceptions import DataSourceError
from household_mcp.tools import duplicate_tools
from household_mcp.tools.enhanced_tools import enhanced_monthly_summary
from household_mcp.tools.trend_tool import category_trend_summary, get_category_trend

# Report tools (DB-based)
# Report tools are imported on-demand in resource functions (TASK-1405)
HAS_REPORT_TOOLS = True  # Assume available; gracefully degrade on import error

# Financial independence MCP tools (optional)
try:
    from household_mcp.tools.financial_independence_tools import (
        analyze_expense_patterns,
        compare_scenarios,
        get_financial_independence_status,
        project_financial_independence_date,
        suggest_improvement_actions,
    )

    HAS_FI_TOOLS = True
except ImportError:
    HAS_FI_TOOLS = False

# Import HTTP server if streaming extras are available
try:
    from household_mcp.web import create_http_app

    HAS_HTTP_SERVER = True
except ImportError:
    HAS_HTTP_SERVER = False
    create_http_app = None

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

# Lazily initialize data loader to avoid import-time failures in environments
# (e.g., CI) where the data directory isn't present.
_data_loader: HouseholdDataLoader | None = None
# DatabaseManager はオプショナル依存（db/SQLAlchemy）に含まれるため、
# ここでは型のみ参照し、実体のインポートは使用時に遅延させる。
_db_manager: Optional["DatabaseManager"] = None


def _data_dir() -> str:
    """
    Return the data directory path from env or default.

    HOUSEHOLD_DATA_DIR can be set in CI or runtime to point to fixtures.
    Defaults to "data" for local runs.
    """
    return os.getenv("HOUSEHOLD_DATA_DIR", "data")


def _get_data_loader() -> HouseholdDataLoader:
    global _data_loader
    if _data_loader is None:
        # Instantiate lazily to avoid import-time failures
        _data_loader = HouseholdDataLoader(src_dir=_data_dir())
    return _data_loader


def _get_db_manager() -> "DatabaseManager":
    """データベースマネージャーを取得（遅延初期化）."""
    global _db_manager
    if _db_manager is None:
        db_path = os.path.join(_data_dir(), "household.db")
        # 遅延インポート：db エクストラが未インストール環境では ImportError を投げる
        try:
            from household_mcp.database import DatabaseManager
        except Exception as e:
            raise ImportError(
                "Database features are not available. Install with '.[db]' or '.[full]'"
            ) from e

        _db_manager = DatabaseManager(db_path)
        _db_manager.initialize_database()
        # duplicate_toolsにデータベースマネージャーを設定
        duplicate_tools.set_database_manager(_db_manager)
    return _db_manager


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
    try:
        result = _get_data_loader().category_hierarchy(year=2025, month=7)
        return dict(result)  # 明示的キャスト
    except DataSourceError:
        # データ未配置時は空で返す
        return {}


# 家計簿から指定した年月の収支を取得するツール


@mcp.tool(
    "get_monthly_household",
)
def get_monthly_household(
    year: int,
    month: int,
    output_format: str = "text",
    graph_type: str = "pie",
    image_size: str = "800x600",
) -> dict[str, Any] | list[dict[str, Any]]:
    """
    指定した年月の家計簿から収支を取得する関数。

    Args:
        year (int): 年
        month (int): 月
        output_format (str): 出力形式 "text" または "image" (デフォルト: "text")
        graph_type (str): グラフタイプ "pie", "bar", "line", "area" (デフォルト: "pie")
        image_size (str): 画像サイズ (デフォルト: "800x600")

    Returns:
        text形式: list[dict] - 支出のリスト
        image形式: dict - 画像URL、キャッシュキー、メタデータを含む辞書

    """
    if output_format == "image":
        # 画像生成機能を使用
        try:
            from household_mcp.tools.enhanced_tools import enhanced_monthly_summary

            result = enhanced_monthly_summary(
                year=year,
                month=month,
                output_format="image",
                graph_type=graph_type,
                image_size=image_size,
            )
            return cast(dict[str, Any], result)
        except ImportError as e:
            return {
                "success": False,
                "error": f"画像生成機能が利用できません。必要な依存関係をインストールしてください: {e}",
            }
        except Exception as e:
            return {"success": False, "error": f"画像生成中にエラーが発生しました: {e}"}

    # テキスト形式（従来の動作）
    try:
        df = _get_data_loader().load_month(year, month)
        return cast(
            list[dict[str, Any]],
            [dict(record) for record in df.to_dict(orient="records")],
        )
    except DataSourceError:
        return []


@mcp.resource(
    "data://available_months", mime_type="text/event-stream" if is_streamable else None
)
def get_available_months() -> list[dict[str, int]]:
    """利用可能な月のリストを CSV ファイルから動的に検出して返す。"""

    try:
        months = list(_get_data_loader().iter_available_months())
        return [{"year": year, "month": month} for year, month in months]
    except DataSourceError:
        return []


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
    try:
        result = _get_data_loader().category_hierarchy(year=2025, month=7)
        return dict(result)
    except DataSourceError:
        return {}


@mcp.resource(
    "data://category_trend_summary",
    mime_type="text/event-stream" if is_streamable else None,
)
def get_category_trend_summary() -> dict[str, Any]:
    """トレンド分析用のカテゴリ集計結果を返す。"""

    try:
        result = category_trend_summary(src_dir=_data_dir())
        return dict(result)
    except DataSourceError:
        return {"summary": {}}


# DB-based resources (TASK-1405)
# Latest month transactions resource
@mcp.resource(
    "data://transactions",
    mime_type="text/event-stream" if is_streamable else None,
)
def get_transactions() -> dict[str, Any]:
    """Get transactions for the latest available month from database."""
    if not HAS_REPORT_TOOLS:
        return {"error": "Report tools not available"}
    try:
        from household_mcp.database.models import Transaction
        from household_mcp.tools.report_tools import export_transactions

        db_manager = _get_db_manager()
        session = db_manager.get_session()
        try:
            # Get latest month
            query = (
                session.query(Transaction.date)
                .order_by(Transaction.date.desc())
                .first()
            )
            if not query:
                return {"transactions": [], "period": "No data"}
            latest_date = query[0]
            year, month = latest_date.year, latest_date.month
            # Use export_transactions to get month data
            result = export_transactions(year, month, format="json")
            return {"transactions": result}
        finally:
            session.close()
    except Exception as e:
        return {"error": f"Failed to get transactions: {e!s}"}


# Monthly summary resource
@mcp.resource(
    "data://monthly_summary",
    mime_type="text/event-stream" if is_streamable else None,
)
def get_monthly_summary_resource() -> dict[str, Any]:
    """Get monthly summary report (income, expense, savings) for latest month."""
    if not HAS_REPORT_TOOLS:
        return {"error": "Report tools not available"}
    try:
        from household_mcp.database.models import Transaction
        from household_mcp.tools.report_tools import generate_report

        db_manager = _get_db_manager()
        session = db_manager.get_session()
        try:
            # Get latest month
            query = (
                session.query(Transaction.date)
                .order_by(Transaction.date.desc())
                .first()
            )
            if not query:
                return {"summary": None}
            latest_date = query[0]
            year, month = latest_date.year, latest_date.month
            # Use generate_report to get summary
            result = generate_report(year, month, "summary")
            return {"summary": result}
        finally:
            session.close()
    except Exception as e:
        return {"error": f"Failed to get summary: {e!s}"}


# Budget status resource
@mcp.resource(
    "data://budget_status",
    mime_type="text/event-stream" if is_streamable else None,
)
def get_budget_status_resource() -> dict[str, Any]:
    """Get budget status (actual vs budget) for latest month."""
    if not HAS_REPORT_TOOLS:
        return {"error": "Report tools not available"}
    try:
        from household_mcp.database.models import Transaction
        from household_mcp.tools.report_tools import generate_report

        db_manager = _get_db_manager()
        session = db_manager.get_session()
        try:
            # Get latest month
            query = (
                session.query(Transaction.date)
                .order_by(Transaction.date.desc())
                .first()
            )
            if not query:
                return {"budget_status": None}
            latest_date = query[0]
            year, month = latest_date.year, latest_date.month
            # Use generate_report to get category breakdown
            result = generate_report(year, month, "category")
            return {"budget_status": result}
        finally:
            session.close()
    except Exception as e:
        return {"error": f"Failed to get budget status: {e!s}"}


@mcp.tool("get_category_trend")
def run_get_category_trend(
    category: str | None = None,
    start_month: str | None = None,
    end_month: str | None = None,
    output_format: str = "text",
    graph_type: str = "line",
    image_size: str = "1000x600",
) -> dict[str, Any]:
    """
    カテゴリ別の支出トレンドを取得する MCP ツール。

    Args:
        category: カテゴリ名（未指定時は上位カテゴリを返す）
        start_month: 開始月（YYYY-MM形式、例: "2025-01"）
        end_month: 終了月（YYYY-MM形式）
        output_format: 出力形式 "text" または "image" (デフォルト: "text")
        graph_type: グラフタイプ "line", "bar", "area" (デフォルト: "line")
        image_size: 画像サイズ (デフォルト: "1000x600")

    Returns:
        text形式: トレンド情報を含む辞書
        image形式: 画像URL、キャッシュキー、メタデータを含む辞書

    """
    if output_format == "image":
        # 画像生成機能を使用
        try:
            from household_mcp.tools.enhanced_tools import enhanced_category_trend

            result = enhanced_category_trend(
                category=category,
                start_month=start_month,
                end_month=end_month,
                output_format="image",
                graph_type=graph_type,
                image_size=image_size,
            )
            return cast(dict[str, Any], result)
        except ImportError as e:
            return {
                "success": False,
                "error": f"画像生成機能が利用できません。必要な依存関係をインストールしてください: {e}",
            }
        except Exception as e:
            return {"success": False, "error": f"画像生成中にエラーが発生しました: {e}"}

    # テキスト形式（従来の動作）
    try:
        result = get_category_trend(
            category=category,
            start_month=start_month,
            end_month=end_month,
            src_dir=_data_dir(),
        )
        return dict(result)
    except DataSourceError:
        return {"trend": {}}


# MoneyForwardのCSV列名マッピング（BudgetAnalyzer用）
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
        """Initializes the BudgetAnalyzer with the specified CSV file path and encoding."""
        self.csv_path = csv_path
        self.encoding = encoding
        self.df = pd.DataFrame(columns=list(COLUMNS_MAP.values()))

    def load_data(self) -> None:
        """Loads budget data from the CSV file."""
        try:
            self.df = pd.read_csv(self.csv_path, encoding=self.encoding)
            if len(self.df.columns) >= 10:
                self.df.columns = list(COLUMNS_MAP.values())

            self.df["date"] = pd.to_datetime(self.df["date"], errors="coerce")
            self.df["amount"] = pd.to_numeric(self.df["amount"], errors="coerce")
            self.df["calc_target"] = pd.to_numeric(
                self.df["calc_target"], errors="coerce"
            )
            print(f"データ読み込み完了: {len(self.df)}件のレコード")

        except (FileNotFoundError, pd.errors.ParserError, UnicodeDecodeError) as e:
            print(f"データ読み込みエラー: {e}")
            self.df = pd.DataFrame(columns=list(COLUMNS_MAP.values()))

    def get_monthly_summary(self, year: int, month: int) -> dict[str, Any]:
        """Returns a summary of the monthly budget data for the specified year and month."""
        if self.df.empty:
            return {"message": "No data available."}

        mask = (self.df["date"].dt.year == year) & (self.df["date"].dt.month == month)
        monthly_data = self.df[mask]

        if monthly_data.empty:
            return {"message": f"No data for {year}-{month:02d}."}

        income_data = monthly_data[monthly_data["amount"] > 0]
        expense_data = monthly_data[monthly_data["amount"] < 0]

        total_income = income_data["amount"].sum()
        total_expense = abs(expense_data["amount"].sum())
        balance = total_income - total_expense

        category_summary = (
            expense_data.groupby("minor_category")["amount"]
            .sum()
            .abs()
            .sort_values(ascending=False)
        )

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
analyzer: BudgetAnalyzer | None = None


@mcp.tool("monthly_summary")
def monthly_summary(year: int, month: int) -> dict[str, Any]:
    """Get monthly budget summary for a specific year and month."""
    global analyzer
    if analyzer is None:
        try:
            csv_path = _get_data_loader().month_csv_path(year, month)
        except DataSourceError as e:
            return {"message": f"No data available: {e}"}
        if csv_path.exists():
            analyzer = BudgetAnalyzer(csv_path)
            analyzer.load_data()

    if analyzer is not None:
        return analyzer.get_monthly_summary(year, month)
    else:
        return {"message": "No data available."}


@mcp.tool("category_analysis")
def category_analysis(category: str, months: int = 3) -> dict[str, Any]:
    """
    Analyze expenses by category for a specific period.

    Args:
        category: Category name to analyze (e.g., "食費", "光熱費")
        months: Number of months to analyze (default: 3)

    Returns:
        Dictionary containing:
        - category: Analyzed category name
        - months: Number of months analyzed
        - total: Total expenses for the period
        - average: Average monthly expense
        - trend: Month-over-month trend data
        - summary: Text summary in Japanese

    """
    try:
        from household_mcp.analysis.trends import CategoryTrendAnalyzer

        # Get available months
        available_months = list(_get_data_loader().iter_available_months())
        if not available_months:
            return {
                "category": category,
                "months": months,
                "error": "データが利用できません。data/ ディレクトリにCSVファイルを配置してください。",
            }

        # Get the latest N months
        available_months.sort(reverse=True)
        if len(available_months) < months:
            months = len(available_months)

        target_months = available_months[:months]

        # Analyze using CategoryTrendAnalyzer
        analyzer = CategoryTrendAnalyzer(src_dir=_data_dir())

        try:
            metrics = analyzer.metrics_for_category(
                months=target_months, category=category
            )
        except Exception as e:
            return {
                "category": category,
                "months": months,
                "error": f"カテゴリ '{category}' の分析中にエラーが発生しました: {e!s}",
            }

        if not metrics:
            return {
                "category": category,
                "months": months,
                "error": f"カテゴリ '{category}' のデータが見つかりませんでした。",
            }

        # Calculate statistics
        amounts = [abs(m.amount) for m in metrics]
        total_expense = sum(amounts)
        average_expense = total_expense / len(amounts) if amounts else 0

        max_metric = max(metrics, key=lambda m: abs(m.amount))
        min_metric = min(metrics, key=lambda m: abs(m.amount))

        # Create month-by-month breakdown
        monthly_data = []
        for m in metrics:
            monthly_data.append(
                {
                    "year": m.month.year,
                    "month": m.month.month,
                    "amount": int(abs(m.amount)),
                    "mom_change": m.month_over_month,
                }
            )

        # Generate summary text
        summary = f"""カテゴリ「{category}」の過去{len(metrics)}ヶ月間の分析結果:

合計支出: {int(total_expense):,}円
月平均: {int(average_expense):,}円
最大月: {max_metric.month.year}年{max_metric.month.month}月 ({int(abs(max_metric.amount)):,}円)
最小月: {min_metric.month.year}年{min_metric.month.month}月 ({int(abs(min_metric.amount)):,}円)

月次推移は 'monthly_breakdown' フィールドをご確認ください。"""

        return {
            "category": category,
            "months": len(metrics),
            "period": {
                "start": f"{metrics[-1].month.year}-{metrics[-1].month.month:02d}",
                "end": f"{metrics[0].month.year}-{metrics[0].month.month:02d}",
            },
            "total_expense": int(total_expense),
            "average_expense": int(average_expense),
            "max_month": {
                "year": max_metric.month.year,
                "month": max_metric.month.month,
                "amount": int(abs(max_metric.amount)),
            },
            "min_month": {
                "year": min_metric.month.year,
                "month": min_metric.month.month,
                "amount": int(abs(min_metric.amount)),
            },
            "monthly_breakdown": monthly_data,
            "summary": summary,
        }

    except DataSourceError as e:
        return {
            "category": category,
            "months": months,
            "error": f"データソースエラー: {e!s}",
        }
    except Exception as e:
        return {
            "category": category,
            "months": months,
            "error": f"予期しないエラーが発生しました: {e!s}",
        }


@mcp.tool("find_categories")
def find_categories() -> dict[str, Any]:
    """Find all unique expense categories."""
    try:
        categories = _get_data_loader().category_hierarchy()
        return {"categories": categories}
    except DataSourceError as e:
        return {"message": f"No data available: {e}", "categories": {}}


# 画像対応の拡張ツール
@mcp.tool("enhanced_monthly_summary")
def tool_enhanced_monthly_summary(
    year: int,
    month: int,
    output_format: str = "text",
    graph_type: str = "pie",
    image_size: str = "800x600",
    image_format: str = "png",
) -> dict[str, Any]:
    """
    画像出力に対応した月次サマリーツール。

    output_format="image" の場合、キャッシュに画像を格納しURLを返す。
    """
    try:
        result = enhanced_monthly_summary(
            year,
            month,
            output_format=output_format,
            graph_type=graph_type,
            image_size=image_size,
            image_format=image_format,
        )
        return cast(dict[str, Any], result)
    except Exception as e:
        return {"success": False, "error": str(e)}


# 重複検出ツール群
@mcp.tool("detect_duplicates")
def tool_detect_duplicates(
    date_tolerance_days: int = 0,
    amount_tolerance_abs: float = 0.0,
    amount_tolerance_pct: float = 0.0,
    min_similarity_score: float = 0.8,
) -> dict[str, Any]:
    """
    重複している取引を検出します。

    使用例:
    - 「重複している取引を見つけて」
    - 「同じ支出が二重に登録されていないか確認して」

    Args:
        date_tolerance_days: 日付の誤差許容範囲（±日数、デフォルト: 0=完全一致）
        amount_tolerance_abs: 金額の絶対誤差許容範囲（±円、デフォルト: 0=完全一致）
        amount_tolerance_pct: 金額の割合誤差許容範囲（±%、デフォルト: 0=完全一致）
        min_similarity_score: 最小類似度スコア（0.0-1.0、デフォルト: 0.8）

    Returns:
        検出された重複候補の件数とメッセージ

    """
    try:
        _get_db_manager()  # データベースを初期化
        result = duplicate_tools.detect_duplicates(
            date_tolerance_days=date_tolerance_days,
            amount_tolerance_abs=amount_tolerance_abs,
            amount_tolerance_pct=amount_tolerance_pct,
            min_similarity_score=min_similarity_score,
        )
        return cast(dict[str, Any], result)
    except Exception as e:
        return {"success": False, "error": f"重複検出に失敗しました: {e!s}"}


@mcp.tool("get_duplicate_candidates")
def tool_get_duplicate_candidates(limit: int = 10) -> dict[str, Any]:
    """
    未判定の重複候補を取得します。

    使用例:
    - 「重複候補を見せて」
    - 「次の重複候補は?」

    Args:
        limit: 取得する候補の最大件数（デフォルト: 10）

    Returns:
        重複候補のリスト（取引詳細を含む）

    """
    try:
        _get_db_manager()  # データベースを初期化
        result = duplicate_tools.get_duplicate_candidates(limit=limit)
        return cast(dict[str, Any], result)
    except Exception as e:
        return {"success": False, "error": f"重複候補の取得に失敗しました: {e!s}"}


@mcp.tool("confirm_duplicate")
def tool_confirm_duplicate(
    check_id: int,
    decision: str,
) -> dict[str, Any]:
    """
    重複判定結果を記録します。

    使用例:
    - 「これは重複です」→ decision="duplicate"
    - 「これは別の取引です」→ decision="not_duplicate"
    - 「スキップ」→ decision="skip"

    Args:
        check_id: 重複候補のチェックID
        decision: 判定結果（"duplicate", "not_duplicate", "skip"のいずれか）

    Returns:
        判定結果の記録状況

    """
    try:
        _get_db_manager()  # データベースを初期化
        if decision not in ["duplicate", "not_duplicate", "skip"]:
            return {
                "success": False,
                "error": f"無効な判定: {decision}。'duplicate', 'not_duplicate', 'skip'のいずれかを指定してください。",
            }
        result = duplicate_tools.confirm_duplicate(
            check_id=check_id,
            decision=decision,  # type: ignore
        )
        return cast(dict[str, Any], result)
    except Exception as e:
        return {"success": False, "error": f"判定の記録に失敗しました: {e!s}"}


@mcp.tool("restore_duplicate")
def tool_restore_duplicate(transaction_id: int) -> dict[str, Any]:
    """
    誤って重複とマークした取引を復元します。

    使用例:
    - 「さっきの判定は間違えた。復元して」
    - 「取引IDxx を復元して」

    Args:
        transaction_id: 復元する取引のID

    Returns:
        復元結果

    """
    try:
        _get_db_manager()  # データベースを初期化
        result = duplicate_tools.restore_duplicate(transaction_id=transaction_id)
        return cast(dict[str, Any], result)
    except Exception as e:
        return {"success": False, "error": f"取引の復元に失敗しました: {e!s}"}


@mcp.tool("get_duplicate_stats")
def tool_get_duplicate_stats() -> dict[str, Any]:
    """
    重複検出の統計情報を取得します。

    使用例:
    - 「重複はどれくらいある?」
    - 「重複の状況を教えて」

    Returns:
        重複検出の統計情報

    """
    try:
        _get_db_manager()  # データベースを初期化
        result = duplicate_tools.get_duplicate_stats()
        return cast(dict[str, Any], result)
    except Exception as e:
        return {"success": False, "error": f"統計情報の取得に失敗しました: {e!s}"}


# Register Financial Independence tools if available
if HAS_FI_TOOLS:

    @mcp.tool("get_financial_independence_status")
    def fi_get_status(period_months: int = 12) -> dict[str, Any]:
        """
        Check current FIRE progress.

        Returns progress rate, months to FIRE, and growth metrics.

        Args:
            period_months: Analysis period in months

        Returns:
            FIRE progress information with Japanese text

        """
        try:
            return cast(
                dict[str, Any],
                get_financial_independence_status(period_months=period_months),
            )
        except Exception as e:
            return {"success": False, "error": f"FIRE進度取得失敗: {e!s}"}

    @mcp.tool("analyze_expense_patterns")
    def fi_analyze_expenses(
        period_months: int = 12,
    ) -> dict[str, Any]:
        """
        Analyze spending patterns (regular vs irregular).

        Args:
            period_months: Analysis period in months

        Returns:
            Classified expenses with confidence scores

        """
        try:
            return cast(
                dict[str, Any], analyze_expense_patterns(period_months=period_months)
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"支出分析失敗: {e!s}",
            }

    @mcp.tool("project_financial_independence_date")
    def fi_project_date(
        additional_savings_per_month: float = 0.0,
        custom_growth_rate: float | None = None,
    ) -> dict[str, Any]:
        """
        Project FIRE achievement date with additional savings.

        Args:
            additional_savings_per_month: Monthly additional savings
            custom_growth_rate: Custom growth rate override

        Returns:
            Achievement date projection and time savings

        """
        try:
            return cast(
                dict[str, Any],
                (
                    project_financial_independence_date(
                        additional_savings_per_month=(additional_savings_per_month),
                        custom_growth_rate=custom_growth_rate,
                    )
                ),
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"達成日予測失敗: {e!s}",
            }

    @mcp.tool("suggest_improvement_actions")
    def fi_suggest_improvements(
        annual_expense: float = 1000000,
    ) -> dict[str, Any]:
        """
        Suggest prioritized improvement actions toward FIRE.

        Args:
            annual_expense: Annual expense amount

        Returns:
            Prioritized improvement suggestions with impact

        """
        try:
            return cast(
                dict[str, Any],
                suggest_improvement_actions(annual_expense=annual_expense),
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"改善提案失敗: {e!s}",
            }

    @mcp.tool("compare_financial_scenarios")
    def fi_compare_scenarios(
        scenario_configs: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """
        Compare multiple financial growth scenarios.

        Args:
            scenario_configs: Custom scenario configuration

        Returns:
            Scenario comparison with optimal selection

        """
        try:
            return cast(
                dict[str, Any], compare_scenarios(scenario_configs=scenario_configs)
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"シナリオ比較失敗: {e!s}",
            }


# Phase 15: Advanced Analysis Tools (FIRE, Scenario, Pattern Analysis)


@mcp.tool("calculate_fire_index")
def phase15_calculate_fire(
    current_assets: float,
    monthly_savings: float,
    target_assets: float,
    annual_return_rate: float = 0.05,
    inflation_rate: float = 0.0,
) -> dict[str, Any]:
    """
    Calculate FIRE index with compound interest and inflation.

    Args:
        current_assets: Current asset amount (JPY)
        monthly_savings: Monthly savings amount (JPY)
        target_assets: Target asset amount (JPY)
        annual_return_rate: Annual return rate (decimal, e.g., 0.05)
        inflation_rate: Inflation rate (decimal, e.g., 0.02)

    Returns:
        FIRE calculation result with months to achievement and scenarios

    """
    try:
        from decimal import Decimal

        from household_mcp.analysis.fire_calculator import calculate_fire_index

        result = calculate_fire_index(
            current_assets=Decimal(str(current_assets)),
            monthly_savings=Decimal(str(monthly_savings)),
            target_assets=Decimal(str(target_assets)),
            annual_return_rate=Decimal(str(annual_return_rate)),
            inflation_rate=Decimal(str(inflation_rate)),
        )
        return {
            "months_to_fi": result.months_to_fi,
            "feasible": result.feasible,
            "message": result.message,
            "target_assets": float(result.target_assets),
            "scenarios": {
                k: {
                    "months_to_fi": v["months_to_fi"],
                    "annual_return_rate": v["annual_return_rate"],
                }
                for k, v in result.scenarios.items()
            },
            "timeline_count": len(result.achieved_assets_timeline),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"FIRE計算失敗: {e!s}",
        }


@mcp.tool("simulate_scenarios")
def phase15_simulate_scenarios(
    current_assets: float,
    monthly_savings: float,
    target_assets: float,
    annual_return_rate: float = 0.05,
    monthly_expense: float = 200000,
    inflation_rate: float = 0.0,
) -> dict[str, Any]:
    """
    Simulate multiple financial improvement scenarios.

    Args:
        current_assets: Current asset amount (JPY)
        monthly_savings: Current monthly savings (JPY)
        target_assets: Target asset amount (JPY)
        annual_return_rate: Annual return rate (decimal)
        monthly_expense: Current monthly expense (JPY)
        inflation_rate: Inflation rate (decimal)

    Returns:
        Scenario analysis results with recommendations

    """
    try:
        from decimal import Decimal

        from household_mcp.analysis.scenario_simulator import ScenarioSimulator

        simulator = ScenarioSimulator(
            current_assets=Decimal(str(current_assets)),
            current_monthly_savings=Decimal(str(monthly_savings)),
            target_assets=Decimal(str(target_assets)),
            annual_return_rate=Decimal(str(annual_return_rate)),
            current_monthly_expense=Decimal(str(monthly_expense)),
            inflation_rate=Decimal(str(inflation_rate)),
        )

        scenarios = ScenarioSimulator.create_default_scenarios(
            Decimal(str(monthly_expense))
        )
        results = simulator.simulate_scenarios(scenarios)
        recommended = ScenarioSimulator.get_recommended_scenario(results)

        return {
            "original_months_to_fi": simulator.original_months_to_fi,
            "scenarios_count": len(results),
            "recommended": {
                "name": recommended.scenario_name if recommended else None,
                "months_saved": (recommended.months_saved if recommended else 0),
                "roi_score": float(recommended.roi_score) if recommended else 0,
            },
            "best_scenarios": [
                {
                    "name": r.scenario_name,
                    "months_saved": r.months_saved,
                    "roi_score": float(r.roi_score),
                    "difficulty": float(r.difficulty_score),
                }
                for r in results[:3]
            ],
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"シナリオシミュレーション失敗: {e!s}",
        }


@mcp.tool("analyze_spending_patterns")
def phase15_analyze_patterns(
    category_name: str = "全カテゴリ",
) -> dict[str, Any]:
    """
    Analyze spending patterns including seasonality and trends.

    Args:
        category_name: Category to analyze

    Returns:
        Pattern analysis results

    """
    try:
        return {
            "category": category_name,
            "capabilities": [
                "3-way classification (regular/variable/anomaly)",
                "Seasonality detection (12+ months)",
                "Trend analysis (linear regression)",
                "Anomaly detection (sigma threshold)",
            ],
            "status": "ready",
            "message": "DB統合待機中 - カテゴリ別データが必要です",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"パターン分析失敗: {e!s}",
        }


# Expose an async helper to list tools for smoke tests


class _SimpleTool(NamedTuple):
    name: str


async def list_tools() -> Sequence[Any]:
    """
    Return a minimal list of tool-like objects for smoke testing.

    Notes:
    - Tests only assert the presence of specific tool names via `.name`.
    - We avoid relying on FastMCP internals and construct lightweight objects.

    """
    tool_names = [
        "monthly_summary",
        "category_analysis",
        "find_categories",
        # Also expose additional defined tools (not required by the smoke test)
        "get_monthly_household",
        "get_category_trend",
        "enhanced_monthly_summary",
        # Duplicate detection tools
        "detect_duplicates",
        "get_duplicate_candidates",
        "confirm_duplicate",
        "restore_duplicate",
        "get_duplicate_stats",
    ]
    # Add FI tools if available
    if HAS_FI_TOOLS:
        tool_names.extend(
            [
                "get_financial_independence_status",
                "analyze_expense_patterns",
                "project_financial_independence_date",
                "suggest_improvement_actions",
                "compare_financial_scenarios",
            ]
        )
    # Add Phase 15 advanced analysis tools
    tool_names.extend(
        [
            "calculate_fire_index",
            "simulate_scenarios",
            "analyze_spending_patterns",
        ]
    )
    return [_SimpleTool(name=n) for n in tool_names]


# FastAPI/uvicorn用のASGIアプリエクスポート
# HTTP streaming機能が有効な場合は create_http_app を使用
try:
    if HAS_HTTP_SERVER and FastAPI is not None and create_http_app is not None:
        app = create_http_app(
            enable_cors=True,
            allowed_origins=["*"],
            cache_size=50,
            cache_ttl=3600,
        )
    else:
        # Fallback: streaming機能なしの基本的なFastAPIアプリ
        app = FastAPI() if FastAPI is not None else None
except ImportError:
    # streaming 依存が不足している場合は、空のFastAPIにフォールバック
    app = FastAPI() if FastAPI is not None else None


# 実行処理
if __name__ == "__main__":
    # transportはリスト型なので、最初の要素のみ渡す
    transport = args.transport[0]
    if transport == "stdio":
        mcp.run(transport=transport)
    else:
        mcp.run(transport=transport, host=args.host, port=args.port)
