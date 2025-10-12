"""家計簿分析MCPサーバー用データベース接続管理.

SQLiteデータベースへの接続管理、コネクションプール、トランザクション管理を提供
"""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

from .models import DatabaseSchema

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """データベース接続管理クラス."""

    def __init__(self, db_path: str = "household.db"):
        """初期化.

        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = Path(db_path)
        self._connection: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()

    def connect(self) -> sqlite3.Connection:
        """データベースに接続."""
        if self._connection is None:
            with self._lock:
                if self._connection is None:
                    try:
                        # データベースディレクトリが存在しない場合は作成
                        self.db_path.parent.mkdir(parents=True, exist_ok=True)

                        # SQLiteに接続
                        self._connection = sqlite3.connect(
                            str(self.db_path),
                            detect_types=sqlite3.PARSE_DECLTYPES
                            | sqlite3.PARSE_COLNAMES,
                            check_same_thread=False,
                        )

                        # 外部キー制約を有効化
                        self._connection.execute("PRAGMA foreign_keys = ON")

                        # WALモードを有効化（同時接続性能向上）
                        self._connection.execute("PRAGMA journal_mode = WAL")

                        # データベーススキーマを作成
                        DatabaseSchema.create_all_tables(self._connection)

                        logger.info("Database connected successfully: %s", self.db_path)

                    except sqlite3.Error as e:
                        logger.error("Failed to connect to database: %s", e)
                        raise

        return self._connection

    def close(self) -> None:
        """データベース接続を閉じる."""
        if self._connection is not None:
            with self._lock:
                if self._connection is not None:
                    try:
                        self._connection.close()
                        self._connection = None
                        logger.info("Database connection closed")
                    except sqlite3.Error as e:
                        logger.error("Error closing database connection: %s", e)

    def __enter__(self):
        """コンテキストマネージャーのエントリ."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了."""
        if exc_type is not None:
            logger.error("Exception occurred in database context: %s", exc_val)
        # 通常は接続を維持（手動でcloseを呼ぶ）

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """トランザクション管理コンテキストマネージャー.

        Yields:
            データベース接続オブジェクト

        Raises:
            sqlite3.Error: データベースエラー
        """
        connection = self.connect()
        savepoint = False
        try:
            # 既にトランザクション中ならSAVEPOINTを使用
            if getattr(connection, "in_transaction", False):
                connection.execute("SAVEPOINT sp_txn")
                savepoint = True
            else:
                # トランザクション開始（自動コミット無効化）
                connection.execute("BEGIN")

            yield connection

            # 正常終了でコミット/リリース
            if savepoint:
                connection.execute("RELEASE SAVEPOINT sp_txn")
            else:
                connection.commit()
            logger.debug("Transaction committed successfully")

        except Exception as e:
            # エラー発生でロールバック
            if savepoint:
                connection.execute("ROLLBACK TO SAVEPOINT sp_txn")
                connection.execute("RELEASE SAVEPOINT sp_txn")
            else:
                connection.rollback()
            logger.error("Transaction rolled back due to error: %s", e)
            raise

    def execute_query(
        self,
        query: str,
        parameters: Optional[tuple] = None,
        fetch_one: bool = False,
        fetch_all: bool = True,
    ) -> Optional[Any]:
        """クエリを実行.

        Args:
            query: 実行するSQL文
            parameters: SQLパラメータ
            fetch_one: 単一行取得フラグ
            fetch_all: 全行取得フラグ

        Returns:
            クエリ結果

        Raises:
            sqlite3.Error: データベースエラー
        """
        connection = self.connect()
        try:
            cursor = connection.cursor()

            if parameters:
                cursor.execute(query, parameters)
            else:
                cursor.execute(query)

            if fetch_one:
                result = cursor.fetchone()
            elif fetch_all:
                result = cursor.fetchall()
            else:
                result = cursor.rowcount

            return result

        except sqlite3.Error as e:
            logger.error("Error executing query: %s", e)
            logger.error("Query: %s", query)
            logger.error("Parameters: %s", parameters)
            raise

    def execute_many(self, query: str, parameters_list: list) -> int:
        """複数レコードの一括処理.

        Args:
            query: 実行するSQL文
            parameters_list: パラメータのリスト

        Returns:
            処理した行数

        Raises:
            sqlite3.Error: データベースエラー
        """
        connection = self.connect()
        try:
            cursor = connection.cursor()
            cursor.executemany(query, parameters_list)
            connection.commit()
            return cursor.rowcount

        except sqlite3.Error as e:
            connection.rollback()
            logger.error("Error executing batch query: %s", e)
            logger.error("Query: %s", query)
            raise

    def get_table_names(self) -> list:
        """データベース内のテーブル名一覧を取得.

        Returns:
            テーブル名のリスト
        """
        query = "SELECT name FROM sqlite_master WHERE type='table'"
        result = self.execute_query(query, fetch_all=True)
        return [row[0] for row in result] if result else []

    def table_exists(self, table_name: str) -> bool:
        """指定されたテーブルが存在するかチェック.

        Args:
            table_name: テーブル名

        Returns:
            テーブルの存在フラグ
        """
        query = """
        SELECT name FROM sqlite_master
        WHERE type='table' AND name=?
        """
        result = self.execute_query(query, (table_name,), fetch_one=True)
        return result is not None

    def get_row_count(self, table_name: str) -> int:
        """指定されたテーブルの行数を取得.

        Args:
            table_name: テーブル名

        Returns:
            行数
        """
        # テーブル名はSQLパラメータとして渡せないため、厳密な検証＋ホワイトリストで安全性を担保
        import re as _re  # local import to avoid top-level dependency at import time

        if not _re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", table_name):
            raise ValueError("Invalid table name")

        allowed_tables = self.get_table_names()
        if table_name not in allowed_tables:
            raise ValueError(f"Table '{table_name}' does not exist or is not allowed")

        # テーブル名はSQLパラメータ化できないため、厳密な検証後のみ埋め込む
        query = f'SELECT COUNT(*) FROM "{table_name}"'  # nosec B608
        result = self.execute_query(query, fetch_one=True)
        return result[0] if result else 0

    def backup_database(self, backup_path: str) -> None:
        """データベースのバックアップを作成.

        Args:
            backup_path: バックアップファイルのパス

        Raises:
            sqlite3.Error: データベースエラー
        """
        try:
            source_conn = self.connect()
            backup_file = Path(backup_path)
            backup_file.parent.mkdir(parents=True, exist_ok=True)

            with sqlite3.connect(str(backup_file)) as backup_conn:
                source_conn.backup(backup_conn)

            logger.info("Database backup created: %s", backup_file)

        except sqlite3.Error as e:
            logger.error("Error creating database backup: %s", e)
            raise

    def vacuum(self) -> None:
        """データベースの最適化を実行."""
        try:
            connection = self.connect()
            connection.execute("VACUUM")
            logger.info("Database vacuum completed")

        except sqlite3.Error as e:
            logger.error("Error during database vacuum: %s", e)
            raise


# グローバルなデータベース接続インスタンス
_db_connection: Optional[DatabaseConnection] = None


def get_database_connection(db_path: str = "data/household.db") -> DatabaseConnection:
    """データベース接続のシングルトンインスタンスを取得.

    Args:
        db_path: データベースファイルのパス

    Returns:
        データベース接続インスタンス
    """
    global _db_connection

    if _db_connection is None:
        _db_connection = DatabaseConnection(db_path)

    return _db_connection


def close_database_connection() -> None:
    """グローバルなデータベース接続を閉じる."""
    global _db_connection

    if _db_connection is not None:
        _db_connection.close()
        _db_connection = None
