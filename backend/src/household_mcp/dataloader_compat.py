"""
互換性レイヤー: CSV DataLoader と SQLite Database を統一インターフェースで操作。

このモジュールは、既存の HouseholdDataLoader（CSV ベース）と新しい
SQLite データベースの間に互換性を提供します。既存コードへの変更を最小化
しながら、データベースをシームレスに統合できます。

主な機能:
- CSV と DB からの統一的なデータアクセス
- キャッシング戦略の継続
- 段階的なマイグレーション対応
- トランザクション管理
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from .exceptions import DataSourceError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

MonthTuple = tuple[int, int]


class DataLoaderBackend(ABC):
    """
    データローダーの抽象基底クラス。

    CSV ベースと DB ベースの異なるバックエンドを統一インターフェースで
    扱うための抽象クラスです。
    """

    @abstractmethod
    def load(self, year: int | None = None, month: int | None = None) -> pd.DataFrame:
        """
        指定期間のデータを読み込む。

        Args:
            year: 年（None の場合はすべての年）
            month: 月（None の場合はすべての月）

        Returns:
            読み込んだデータの DataFrame

        Raises:
            DataSourceError: データが見つからない場合

        """

    @abstractmethod
    def load_month(self, year: int, month: int) -> pd.DataFrame:
        """指定月のデータを読み込む（キャッシュ有り）。"""

    @abstractmethod
    def load_many(self, months: Sequence[MonthTuple]) -> pd.DataFrame:
        """複数月のデータを読み込む。"""

    @abstractmethod
    def iter_available_months(self) -> Generator[MonthTuple, None, None]:
        """利用可能な年月をすべて列挙する。"""

    @abstractmethod
    def category_hierarchy(
        self, *, year: int | None = None, month: int | None = None
    ) -> dict[str, list[str]]:
        """カテゴリ階層を取得する（大項目→中項目）。"""

    @abstractmethod
    def clear_cache(self) -> None:
        """キャッシュをクリアする。"""

    @abstractmethod
    def cache_stats(self) -> dict[str, int]:
        """キャッシュ統計を取得する。"""


class CSVBackend(DataLoaderBackend):
    """CSV ファイルベースのバックエンド（既存の HouseholdDataLoader をラップ）。"""

    def __init__(self, src_dir: str | Path = "data") -> None:
        # 遅延インポート（dataloader との循環参照を回避）
        from .dataloader import HouseholdDataLoader

        self._loader = HouseholdDataLoader(src_dir=src_dir)

    def load(self, year: int | None = None, month: int | None = None) -> pd.DataFrame:
        return self._loader.load(year=year, month=month)

    def load_month(self, year: int, month: int) -> pd.DataFrame:
        return self._loader.load_month(year, month)

    def load_many(self, months: Sequence[MonthTuple]) -> pd.DataFrame:
        return self._loader.load_many(months)

    def iter_available_months(self) -> Generator[MonthTuple, None, None]:
        return self._loader.iter_available_months()

    def category_hierarchy(
        self, *, year: int | None = None, month: int | None = None
    ) -> dict[str, list[str]]:
        return self._loader.category_hierarchy(year=year, month=month)

    def clear_cache(self) -> None:
        self._loader.clear_cache()

    def cache_stats(self) -> dict[str, int]:
        return self._loader.cache_stats()


class SQLiteBackend(DataLoaderBackend):
    """
    SQLite データベースベースのバックエンド。

    SQLAlchemy ORM を使用して、Transaction テーブルからデータを取得し、
    CSV 互換の DataFrame に変換します。
    """

    def __init__(self, session: Session | None = None) -> None:
        """
        SQLite バックエンドを初期化。

        Args:
            session: SQLAlchemy セッション。None の場合は DatabaseManager で作成

        """
        self._session = session
        self._month_cache: dict[MonthTuple, tuple[pd.DataFrame, int]] = {}
        self._cache_hits = 0
        self._cache_misses = 0

    def _get_session(self) -> Session:
        """セッションを取得（キャッシュまたは新規作成）。"""
        if self._session is not None:
            return self._session

        from household_mcp.database.manager import DatabaseManager

        manager = DatabaseManager()
        return manager.get_session()

    def _transactions_to_dataframe(self, transactions: list[object]) -> pd.DataFrame:
        """
        Transaction ORM オブジェクトを DataFrame に変換。

        CSV 形式との互換性を保つため、必要なカラムを追加します。
        """
        if not transactions:
            return pd.DataFrame(
                columns=[
                    "計算対象",
                    "金額（円）",
                    "日付",
                    "大項目",
                    "中項目",
                    "年月",
                    "年月キー",
                    "カテゴリ",
                ]
            )

        data = []
        for tx in transactions:
            # type: ignore - ORM オブジェクトの動的アクセス
            data.append(
                {
                    "計算対象": tx.is_target,  # type: ignore
                    "金額（円）": tx.amount,  # type: ignore
                    "日付": tx.date,  # type: ignore
                    "大項目": tx.category_major or "未分類",  # type: ignore
                    "中項目": tx.category_minor or "未分類",  # type: ignore
                    "年月": pd.Timestamp(tx.date)  # type: ignore
                    .to_period("M")
                    .to_timestamp(),
                    "年月キー": tx.date.strftime("%Y-%m"),  # type: ignore
                    "カテゴリ": tx.category_major or "未分類",  # type: ignore
                }
            )

        df = pd.DataFrame(data)
        # カテゴリをカテゴリ型に変換（CSV との互換性）
        df["大項目"] = df["大項目"].astype("category")
        df["中項目"] = df["中項目"].astype("category")
        df["カテゴリ"] = df["大項目"]

        return df

    def load(self, year: int | None = None, month: int | None = None) -> pd.DataFrame:
        """指定期間のトランザクションを読み込む。"""
        from sqlalchemy import extract, select

        from household_mcp.database.models import Transaction

        session = self._get_session()
        try:
            query = select(Transaction)

            if year is not None:
                query = query.where(extract("year", Transaction.date) == year)

            if month is not None:
                query = query.where(extract("month", Transaction.date) == month)

            query = query.order_by(Transaction.date, Transaction.category_major)

            transactions = session.execute(query).scalars().all()

            if not transactions:
                msg = (
                    f"指定条件に該当するデータがありません (year={year}, month={month})"
                )
                raise DataSourceError(msg)

            return self._transactions_to_dataframe(transactions)
        finally:
            if self._session is None:
                session.close()

    def load_month(self, year: int, month: int) -> pd.DataFrame:
        """
        指定月のトランザクションを読み込む（キャッシュ有り）。

        キャッシュキーは (year, month) とデータベースの更新時刻の
        組み合わせです。
        """
        from sqlalchemy import and_, extract, func, select

        from household_mcp.database.models import Transaction

        key = (year, month)
        session = self._get_session()

        try:
            # キャッシュのタイムスタンプを確認
            count_query = select(func.count(Transaction.id)).where(
                and_(
                    extract("year", Transaction.date) == year,
                    extract("month", Transaction.date) == month,
                )
            )
            record_count = session.execute(count_query).scalar() or 0

            cached = self._month_cache.get(key)
            if cached and cached[1] == record_count:
                self._cache_hits += 1
                return cached[0].copy()

            self._cache_misses += 1
            df = self.load(year=year, month=month)
            self._month_cache[key] = (df, record_count)
            return df.copy()
        finally:
            if self._session is None:
                session.close()

    def load_many(self, months: Sequence[MonthTuple]) -> pd.DataFrame:
        """複数月のトランザクションを読み込む。"""
        if not months:
            raise DataSourceError("対象月が指定されていません")

        frames = []
        for year, month in months:
            frames.append(self.load_month(year, month))

        return pd.concat(frames, ignore_index=True)

    def iter_available_months(
        self,
    ) -> Generator[MonthTuple, None, None]:
        """利用可能な年月をすべて列挙する（DB から）。"""
        from sqlalchemy import extract, select

        from household_mcp.database.models import Transaction

        session = self._get_session()
        try:
            query = (
                select(
                    extract("year", Transaction.date),
                    extract("month", Transaction.date),
                )
                .distinct()
                .order_by(
                    extract("year", Transaction.date),
                    extract("month", Transaction.date),
                )
            )

            results = session.execute(query).all()
            for year, month in results:
                yield (int(year), int(month))
        finally:
            if self._session is None:
                session.close()

    def category_hierarchy(
        self, *, year: int | None = None, month: int | None = None
    ) -> dict[str, list[str]]:
        """カテゴリ階層を取得する（DB から）。"""
        df = self.load(year=year, month=month)

        groups: dict[str, list[str]] = {}
        for name, group in df.groupby("大項目", observed=False):
            mids = sorted(group["中項目"].dropna().astype(str).unique())
            groups[str(name)] = mids

        return groups

    def clear_cache(self) -> None:
        """キャッシュをクリアする。"""
        self._month_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def cache_stats(self) -> dict[str, int]:
        """キャッシュ統計を取得する。"""
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "size": len(self._month_cache),
        }


class DataLoaderAdapter:
    """
    CSV と SQLite の統一インターフェース。

    既存の HouseholdDataLoader API と完全な互換性を提供しながら、
    SQLite バックエンドへの透過的な切り替えを実現します。

    使用例:
        # CSV ベース（従来の使用方法）
        loader = DataLoaderAdapter(backend_type="csv", csv_dir="data")

        # SQLite ベース（新方式）
        loader = DataLoaderAdapter(backend_type="sqlite")

        # どちらでも同じインターフェース
        df = loader.load_month(2024, 1)
        months = list(loader.iter_available_months())
    """

    def __init__(
        self,
        backend_type: str = "csv",
        csv_dir: str | Path | None = None,
        db_session: Session | None = None,
    ) -> None:
        """
        DataLoaderAdapter を初期化。

        Args:
            backend_type: "csv" または "sqlite"
            csv_dir: CSV バックエンド用のディレクトリ（デフォルト: "data"）
            db_session: SQLite バックエンド用のセッション

        Raises:
            ValueError: backend_type が不正な場合

        """
        if backend_type not in ("csv", "sqlite"):
            msg = f"Unknown backend_type: {backend_type}"
            raise ValueError(msg)

        self._backend_type = backend_type
        self._backend: DataLoaderBackend

        if backend_type == "csv":
            csv_path = Path(csv_dir) if csv_dir else Path("data")
            self._backend = CSVBackend(src_dir=csv_path)
            logger.info("DataLoaderAdapter: CSV バックエンド初期化 (%s)", csv_path)
        else:
            self._backend = SQLiteBackend(session=db_session)
            logger.info("DataLoaderAdapter: SQLite バックエンド初期化")

    @property
    def backend_type(self) -> str:
        """現在のバックエンドタイプを取得。"""
        return self._backend_type

    def load(self, year: int | None = None, month: int | None = None) -> pd.DataFrame:
        """指定期間のデータを読み込む。"""
        return self._backend.load(year=year, month=month)

    def load_month(self, year: int, month: int) -> pd.DataFrame:
        """指定月のデータを読み込む（キャッシュ有り）。"""
        return self._backend.load_month(year, month)

    def load_many(self, months: Sequence[MonthTuple]) -> pd.DataFrame:
        """複数月のデータを読み込む。"""
        return self._backend.load_many(months)

    def iter_available_months(
        self,
    ) -> Generator[MonthTuple, None, None]:
        """利用可能な年月をすべて列挙する。"""
        return self._backend.iter_available_months()

    def category_hierarchy(
        self, *, year: int | None = None, month: int | None = None
    ) -> dict[str, list[str]]:
        """カテゴリ階層を取得する（大項目→中項目）。"""
        return self._backend.category_hierarchy(year=year, month=month)

    def clear_cache(self) -> None:
        """キャッシュをクリアする。"""
        self._backend.clear_cache()

    def cache_stats(self) -> dict[str, int]:
        """キャッシュ統計を取得する。"""
        return self._backend.cache_stats()


__all__ = [
    "CSVBackend",
    "DataLoaderAdapter",
    "DataLoaderBackend",
    "SQLiteBackend",
]
