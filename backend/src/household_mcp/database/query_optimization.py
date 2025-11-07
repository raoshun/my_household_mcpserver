"""
データベース クエリ最適化と分析モジュール。

このモジュールは、SQLite データベースの クエリ性能最適化と
インデックス戦略、クエリプラン分析を提供します。

主な機能:
- インデックス戦略の設計と検証
- クエリプラン分析と最適化提案
- 集計クエリの性能チューニング
- 統計情報の収集と分析
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from sqlalchemy import func, text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass
class QueryPlan:
    """クエリプランの分析結果。"""

    query_text: str
    explain_plan: list[tuple[int, int, int, str]]
    rows_returned: int
    estimated_cost: float
    use_indexes: list[str]
    recommendation: str | None = None


@dataclass
class IndexStrategy:
    """インデックス戦略の定義。"""

    index_name: str
    table_name: str
    columns: list[str]
    is_unique: bool = False
    reason: str = ""


class QueryOptimizer:
    """
    クエリ最適化と分析クラス。

    SQLite のクエリプランと統計情報を分析し、
    インデックス戦略とクエリ最適化を提案します。
    """

    def __init__(self, session: Session) -> None:
        """
        初期化。

        Args:
            session: SQLAlchemy セッション

        """
        self._session = session

    def analyze_query_plan(self, query_text: str) -> QueryPlan:
        """
        クエリプランを分析。

        Args:
            query_text: SQL クエリテキスト

        Returns:
            QueryPlan: クエリプラン分析結果

        """
        # EXPLAIN QUERY PLAN を実行
        explain_query = f"EXPLAIN QUERY PLAN {query_text}"
        result = self._session.execute(text(explain_query))
        explain_plan = [row for row in result.fetchall()]

        # インデックス使用情報を抽出
        use_indexes = self._extract_indexes_from_plan(explain_plan)

        # クエリプランから推定コストを計算
        estimated_cost = self._calculate_plan_cost(explain_plan)

        # 最適化提案を生成
        recommendation = self._generate_recommendation(use_indexes, explain_plan)

        return QueryPlan(
            query_text=query_text,
            explain_plan=explain_plan,
            rows_returned=len(explain_plan),
            estimated_cost=estimated_cost,
            use_indexes=use_indexes,
            recommendation=recommendation,
        )

    def get_index_strategies(self) -> list[IndexStrategy]:
        """
        推奨インデックス戦略を取得。

        Returns:
            list[IndexStrategy]: インデックス戦略のリスト

        """
        strategies = [
            IndexStrategy(
                index_name="idx_transaction_category_month",
                table_name="transactions",
                columns=["category_major", "category_minor", "date"],
                reason="月次・カテゴリ別集計クエリの高速化",
            ),
            IndexStrategy(
                index_name="idx_transaction_date_amount",
                table_name="transactions",
                columns=["date", "amount"],
                reason="日付・金額範囲検索の最適化",
            ),
            IndexStrategy(
                index_name="idx_asset_date_class",
                table_name="asset_records",
                columns=["date", "asset_class_id"],
                reason="資産クラス別の時系列検索最適化",
            ),
            IndexStrategy(
                index_name="idx_asset_value_date",
                table_name="asset_records",
                columns=["asset_value", "date"],
                reason="資産額の時系列追跡の高速化",
            ),
            IndexStrategy(
                index_name="idx_expense_classification_category",
                table_name="expense_classification",
                columns=["category_major", "regularity"],
                reason="支出分類の規則性分析の高速化",
            ),
        ]
        return strategies

    def get_table_stats(self) -> dict[str, Any]:
        """
        テーブルの統計情報を取得。

        Returns:
            dict: テーブル名をキー、統計情報を値とした辞書

        """
        tables = [
            "transactions",
            "asset_records",
            "assets_classes",
            "duplicate_checks",
            "expense_classification",
            "fi_progress_cache",
        ]

        stats = {}
        for table_name in tables:
            try:
                # レコード数を取得
                count_result = self._session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                record_count = count_result.scalar() or 0

                # テーブルサイズを取得
                size_query = (
                    "SELECT page_count * page_size FROM "
                    "(SELECT COUNT(*) as page_count FROM pragma_page_count) "
                    "CROSS JOIN (SELECT page_size FROM pragma_page_size)"
                )
                size_result = self._session.execute(text(size_query))
                table_size = size_result.scalar() or 0

                stats[table_name] = {
                    "record_count": record_count,
                    "table_size_bytes": table_size,
                    "avg_record_size_bytes": (
                        table_size / record_count if record_count > 0 else 0
                    ),
                }
            except Exception as e:
                logger.warning("Failed to get stats for table %s: %s", table_name, e)
                stats[table_name] = {"error": str(e)}

        return stats

    def _extract_indexes_from_plan(self, plan: list[tuple]) -> list[str]:
        """クエリプランからインデックス使用情報を抽出。"""
        indexes = []
        for row in plan:
            if len(row) >= 4:
                detail = str(row[3])
                # SQLite EXPLAIN 出力でインデックス名を検出
                if "INDEX" in detail:
                    # インデックス名を抽出（簡略版）
                    parts = detail.split()
                    for i, part in enumerate(parts):
                        if "INDEX" in part and i + 1 < len(parts):
                            indexes.append(parts[i + 1])
        return list(set(indexes))  # 重複を除去

    def _calculate_plan_cost(self, plan: list[tuple]) -> float:
        """クエリプランから推定コストを計算。"""
        # SQLite の EXPLAIN QUERY PLAN では明示的なコストが出ない
        # 計画ステップ数を簡略的なコスト推定として使用
        if not plan:
            return 1.0
        return float(len(plan))

    def _generate_recommendation(
        self, use_indexes: list[str], plan: list[tuple]
    ) -> str | None:
        """クエリプランから最適化提案を生成。"""
        # フルテーブルスキャンを検出（SCAN TABLE）
        has_full_scan = any(
            "SCAN TABLE" in str(row[3]) for row in plan if len(row) >= 4
        )

        if has_full_scan:
            return "⚠️ フルテーブルスキャンが検出されました。"
            "対応するインデックスの追加を検討してください。"

        if not use_indexes:
            return (
                "ℹ️ このクエリはインデックスを使用していません。"
                "検索条件に応じてインデックスの追加を検討してください。"
            )

        return "✅ インデックスを効果的に使用しています。"


class AggregationOptimizer:
    """
    集計クエリの最適化クラス。

    月次・カテゴリ別の集計クエリを最適化し、
    パフォーマンスを改善します。
    """

    def __init__(self, session: Session) -> None:
        """
        初期化。

        Args:
            session: SQLAlchemy セッション

        """
        self._session = session

    def get_monthly_category_summary(self, year: int, month: int) -> pd.DataFrame:
        """
        月次カテゴリ別サマリを取得（最適化版）。

        Args:
            year: 年
            month: 月

        Returns:
            pd.DataFrame: カテゴリ別集計結果

        """
        from household_mcp.database.models import Transaction

        # SQLAlchemy ORM を使用して効率的なクエリを構築
        query = (
            self._session.query(
                Transaction.category_major,
                Transaction.category_minor,
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("total_amount"),
                func.avg(Transaction.amount).label("avg_amount"),
            )
            .filter(
                func.extract("year", Transaction.date) == year,
                func.extract("month", Transaction.date) == month,
            )
            .group_by(Transaction.category_major, Transaction.category_minor)
            .order_by(func.sum(Transaction.amount).desc())
        )

        # DataFrame に変換
        df = pd.read_sql(query.statement, self._session.connection())
        return df

    def get_date_range_summary(
        self, start_date: datetime, end_date: datetime
    ) -> pd.DataFrame:
        """
        日付範囲のサマリを取得（最適化版）。

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            pd.DataFrame: 日付別集計結果

        """
        from household_mcp.database.models import Transaction

        query = (
            self._session.query(
                func.date(Transaction.date).label("date"),
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("total_amount"),
            )
            .filter(
                Transaction.date >= start_date,
                Transaction.date <= end_date,
            )
            .group_by(func.date(Transaction.date))
            .order_by(func.date(Transaction.date))
        )

        df = pd.read_sql(query.statement, self._session.connection())
        return df

    def get_top_categories(self, limit: int = 10) -> pd.DataFrame:
        """
        支出が多いカテゴリ TOP N を取得（最適化版）。

        Args:
            limit: 取得上限件数

        Returns:
            pd.DataFrame: トップカテゴリ

        """
        from household_mcp.database.models import Transaction

        query = (
            self._session.query(
                Transaction.category_major,
                func.count(Transaction.id).label("count"),
                func.sum(Transaction.amount).label("total_amount"),
                func.avg(Transaction.amount).label("avg_amount"),
            )
            .group_by(Transaction.category_major)
            .order_by(func.sum(Transaction.amount).desc())
            .limit(limit)
        )

        df = pd.read_sql(query.statement, self._session.connection())
        return df


class IndexManager:
    """
    インデックス管理クラス。

    インデックスの作成・削除・統計情報の管理を行います。
    """

    def __init__(self, session: Session) -> None:
        """
        初期化。

        Args:
            session: SQLAlchemy セッション

        """
        self._session = session

    def create_index(
        self,
        index_name: str,
        table_name: str,
        columns: list[str],
        is_unique: bool = False,
    ) -> bool:
        """
        インデックスを作成。

        Args:
            index_name: インデックス名
            table_name: テーブル名
            columns: カラム名のリスト
            is_unique: ユニークインデックスかどうか

        Returns:
            bool: 成功したかどうか

        """
        try:
            columns_str = ", ".join(columns)
            sql = (
                f"CREATE INDEX IF NOT EXISTS {index_name} "
                f"ON {table_name} ({columns_str})"
            )
            if is_unique:
                sql = sql.replace("INDEX", "UNIQUE INDEX")

            self._session.execute(text(sql))
            self._session.commit()
            logger.info(
                f"インデックス {index_name} を作成しました ({table_name}.{columns_str})"
            )
            return True
        except Exception as e:
            logger.error(f"インデックス作成エラー: {e}")
            return False

    def get_existing_indexes(self) -> dict[str, list[dict[str, Any]]]:
        """
        既存のインデックス情報を取得。

        Returns:
            dict: テーブル名をキー、インデックス情報を値とした辞書

        """
        indexes: dict[str, list[dict[str, Any]]] = {}
        tables = [
            "transactions",
            "asset_records",
            "assets_classes",
            "duplicate_checks",
            "expense_classification",
            "fi_progress_cache",
        ]

        for table_name in tables:
            try:
                result = self._session.execute(text(f"PRAGMA index_list({table_name})"))
                indexes[table_name] = [
                    {
                        "index_name": row[1],
                        "unique": bool(row[2]),
                        "partial": bool(row[4]),
                    }
                    for row in result.fetchall()
                ]
            except Exception as e:
                logger.warning(f"Failed to get indexes for {table_name}: {e}")
                indexes[table_name] = []

        return indexes

    def analyze_statistics(self) -> bool:
        """
        テーブルの統計情報を分析・更新。

        Returns:
            bool: 成功したかどうか

        """
        try:
            self._session.execute(text("ANALYZE"))
            self._session.commit()
            logger.info("統計情報を更新しました")
            return True
        except Exception as e:
            logger.error(f"統計情報の更新エラー: {e}")
            return False

    def vacuum(self) -> bool:
        """
        データベースの最適化（VACUUM）を実行。

        Returns:
            bool: 成功したかどうか

        """
        try:
            self._session.execute(text("VACUUM"))
            self._session.commit()
            logger.info("データベースを最適化しました")
            return True
        except Exception as e:
            logger.error(f"VACUUM エラー: {e}")
            return False


__all__ = [
    "AggregationOptimizer",
    "IndexManager",
    "IndexStrategy",
    "QueryOptimizer",
    "QueryPlan",
]
