"""家計簿分析MCPサーバー用データベースマイグレーション機能.

データベースの初期化、アップグレード、ダウングレード機能を提供
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from .connection import DatabaseConnection
from .models import DatabaseSchema

logger = logging.getLogger(__name__)


class Migration:
    """個別マイグレーションクラス."""

    def __init__(
        self,
        version: str,
        description: str,
        up_sql: List[str],
        down_sql: Optional[List[str]] = None,
    ):
        """初期化.

        Args:
            version: マイグレーションバージョン
            description: マイグレーションの説明
            up_sql: アップグレード用SQL文のリスト
            down_sql: ダウングレード用SQL文のリスト
        """
        self.version = version
        self.description = description
        self.up_sql = up_sql
        self.down_sql = down_sql or []
        self.created_at = datetime.now()

    def apply_up(self, connection: sqlite3.Connection) -> None:
        """アップグレードマイグレーションを適用.

        Args:
            connection: データベース接続

        Raises:
            sqlite3.Error: マイグレーション実行エラー
        """
        try:
            cursor = connection.cursor()
            for sql in self.up_sql:
                if sql.strip():  # 空でないSQL文のみ実行
                    cursor.execute(sql)
            connection.commit()
            logger.info("Applied migration %s: %s", self.version, self.description)

        except sqlite3.Error as e:
            connection.rollback()
            logger.error("Failed to apply migration %s: %s", self.version, e)
            raise

    def apply_down(self, connection: sqlite3.Connection) -> None:
        """ダウングレードマイグレーションを適用.

        Args:
            connection: データベース接続

        Raises:
            sqlite3.Error: マイグレーション実行エラー
        """
        if not self.down_sql:
            raise ValueError(f"No down migration defined for {self.version}")

        try:
            cursor = connection.cursor()
            for sql in self.down_sql:
                if sql.strip():  # 空でないSQL文のみ実行
                    cursor.execute(sql)
            connection.commit()
            logger.info("Reverted migration %s: %s", self.version, self.description)

        except sqlite3.Error as e:
            connection.rollback()
            logger.error("Failed to revert migration %s: %s", self.version, e)
            raise


class MigrationManager:
    """マイグレーション管理クラス."""

    def __init__(self, db_connection: DatabaseConnection):
        """初期化.

        Args:
            db_connection: データベース接続管理インスタンス
        """
        self.db_connection = db_connection
        self.migrations: List[Migration] = []
        self._init_migration_table()
        self._register_migrations()

    def _init_migration_table(self) -> None:
        """マイグレーション管理テーブルを初期化."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        try:
            connection = self.db_connection.connect()
            cursor = connection.cursor()
            cursor.execute(create_table_sql)
            connection.commit()
            logger.debug("Migration table initialized")

        except sqlite3.Error as e:
            logger.error("Failed to initialize migration table: %s", e)
            raise

    def _register_migrations(self) -> None:
        """利用可能なマイグレーションを登録."""
        # 初期マイグレーション: 基本テーブル作成
        initial_migration = Migration(
            version="001_initial_schema",
            description="Create initial database schema with basic tables",
            up_sql=DatabaseSchema.CREATE_TABLES_SQL
            + DatabaseSchema.CREATE_INDEXES_SQL
            + DatabaseSchema.INSERT_DEFAULT_DATA_SQL,
            down_sql=[
                "DROP TABLE IF EXISTS budgets",
                "DROP TABLE IF EXISTS transactions",
                "DROP TABLE IF EXISTS accounts",
                "DROP TABLE IF EXISTS categories",
            ],
        )
        self.migrations.append(initial_migration)

        # 追加のマイグレーション例
        category_enhancement = Migration(
            version="002_enhance_categories",
            description="Add enhanced category features",
            up_sql=[
                """ALTER TABLE categories ADD COLUMN sort_order INTEGER DEFAULT 0.""",
                """
                ALTER TABLE categories ADD COLUMN is_active BOOLEAN DEFAULT 1
                """,
                """CREATE INDEX IF NOT EXISTS idx_categories_sort_order ON
                categories(sort_order)""",
            ],
            down_sql=[
                "DROP INDEX IF EXISTS idx_categories_sort_order",
                # SQLiteではALTER TABLE DROP COLUMNがサポートされていないため
                # 完全なテーブル再作成が必要だがここでは省略
            ],
        )
        self.migrations.append(category_enhancement)

        # アカウント残高履歴テーブルの追加
        balance_history = Migration(
            version="003_account_balance_history",
            description="Add account balance history tracking",
            up_sql=[
                """CREATE TABLE IF NOT EXISTS account_balance_history ( id INTEGER
                PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, balance
                DECIMAL(10,2) NOT NULL, recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (account_id) REFERENCES accounts(id) )
                """,
                """
                CREATE INDEX IF NOT EXISTS idx_balance_history_account
                ON account_balance_history(account_id)
                """,
                """CREATE INDEX IF NOT EXISTS idx_balance_history_date ON
                account_balance_history(recorded_at)""",
            ],
            down_sql=[
                "DROP TABLE IF EXISTS account_balance_history",
            ],
        )
        self.migrations.append(balance_history)

    def get_applied_migrations(self) -> List[str]:
        """適用済みマイグレーションのバージョンリストを取得.

        Returns:
            適用済みマイグレーションバージョンのリスト
        """
        query = "SELECT version FROM schema_migrations ORDER BY version"
        try:
            result = self.db_connection.execute_query(query, fetch_all=True)
            return [row[0] for row in result] if result else []

        except sqlite3.Error as e:
            logger.error("Failed to get applied migrations: %s", e)
            return []

    def get_pending_migrations(self) -> List[Migration]:
        """未適用マイグレーションのリストを取得.

        Returns:
            未適用マイグレーションのリスト
        """
        applied_versions = set(self.get_applied_migrations())
        return [
            migration
            for migration in self.migrations
            if migration.version not in applied_versions
        ]

    def apply_migration(self, migration: Migration) -> bool:
        """単一マイグレーションを適用.

        Args:
            migration: 適用するマイグレーション

        Returns:
            適用成功フラグ
        """
        try:
            with self.db_connection.transaction() as connection:
                # マイグレーション適用
                migration.apply_up(connection)

                # マイグレーション記録を保存
                cursor = connection.cursor()
                cursor.execute(
                    """INSERT INTO schema_migrations (version, description) VALUES (?,
                    ?)""",
                    (migration.version, migration.description),
                )

            logger.info("Successfully applied migration: %s", migration.version)
            return True

        except Exception as e:
            logger.error("Failed to apply migration %s: %s", migration.version, e)
            return False

    def revert_migration(self, migration: Migration) -> bool:
        """単一マイグレーションを取り消し.

        Args:
            migration: 取り消すマイグレーション

        Returns:
            取り消し成功フラグ
        """
        try:
            with self.db_connection.transaction() as connection:
                # マイグレーション取り消し
                migration.apply_down(connection)

                # マイグレーション記録を削除
                cursor = connection.cursor()
                cursor.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (migration.version,),
                )

            logger.info("Successfully reverted migration: %s", migration.version)
            return True

        except Exception as e:
            logger.error("Failed to revert migration %s: %s", migration.version, e)
            return False

    def migrate_up(self, target_version: Optional[str] = None) -> bool:
        """マイグレーションを最新または指定バージョンまで適用.

        Args:
            target_version: 目標バージョン（Noneの場合は最新まで）

        Returns:
            マイグレーション成功フラグ
        """
        pending_migrations = self.get_pending_migrations()

        if not pending_migrations:
            logger.info("No pending migrations found")
            return True

        # ターゲットバージョンが指定されている場合はフィルタリング
        if target_version:
            pending_migrations = [
                m for m in pending_migrations if m.version <= target_version
            ]

        # バージョン順にソートして適用
        pending_migrations.sort(key=lambda m: m.version)

        success_count = 0
        for migration in pending_migrations:
            if self.apply_migration(migration):
                success_count += 1
            else:
                logger.error("Migration failed, stopping at: %s", migration.version)
                break

        logger.info(
            "Applied %d out of %d migrations", success_count, len(pending_migrations)
        )
        return success_count == len(pending_migrations)

    def migrate_down(self, target_version: str) -> bool:
        """指定バージョンまでマイグレーションを取り消し.

        Args:
            target_version: 目標バージョン

        Returns:
            マイグレーション取り消し成功フラグ
        """
        applied_versions = self.get_applied_migrations()
        migrations_to_revert = [
            migration
            for migration in self.migrations
            if migration.version in applied_versions
            and migration.version > target_version
        ]

        if not migrations_to_revert:
            logger.info("No migrations to revert")
            return True

        # 逆順でソート（新しいものから取り消し）
        migrations_to_revert.sort(key=lambda m: m.version, reverse=True)

        success_count = 0
        for migration in migrations_to_revert:
            if self.revert_migration(migration):
                success_count += 1
            else:
                logger.error(
                    "Migration revert failed, stopping at: %s", migration.version
                )
                break

        logger.info(
            "Reverted %d out of %d migrations", success_count, len(migrations_to_revert)
        )
        return success_count == len(migrations_to_revert)

    def get_migration_status(self) -> Dict[str, Any]:
        """マイグレーション状態の取得.

        Returns:
            マイグレーション状態情報
        """
        applied_migrations = self.get_applied_migrations()
        pending_migrations = self.get_pending_migrations()

        return {
            "database_exists": self.db_connection.table_exists("schema_migrations"),
            "total_migrations": len(self.migrations),
            "applied_count": len(applied_migrations),
            "pending_count": len(pending_migrations),
            "applied_migrations": applied_migrations,
            "pending_migrations": [m.version for m in pending_migrations],
            "current_version": applied_migrations[-1] if applied_migrations else None,
            "latest_version": (
                self.migrations[-1].version if self.migrations else None
            ),
        }

    def reset_database(self) -> bool:
        """データベースを完全にリセット.

        Returns:
            リセット成功フラグ
        """
        try:
            # 全てのテーブルを削除
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()

                # 外部キー制約を一時的に無効化
                cursor.execute("PRAGMA foreign_keys = OFF")

                # 全てのテーブルを取得して削除
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]

                for table in tables:
                    cursor.execute(f"DROP TABLE IF EXISTS {table}")

                # 外部キー制約を再有効化
                cursor.execute("PRAGMA foreign_keys = ON")

            # マイグレーション管理テーブルを再初期化
            self._init_migration_table()

            logger.info("Database reset completed")
            return True

        except Exception as e:
            logger.error("Failed to reset database: %s", e)
            return False


def create_migration_manager(db_path: str = "data/household.db") -> MigrationManager:
    """マイグレーション管理インスタンスを作成.

    Args:
        db_path: データベースファイルのパス

    Returns:
        マイグレーション管理インスタンス
    """
    from .connection import get_database_connection

    db_connection = get_database_connection(db_path)
    return MigrationManager(db_connection)
