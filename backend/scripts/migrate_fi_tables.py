#!/usr/bin/env python3
"""
FIRE分析テーブル用マイグレーション スクリプト

新しいテーブルを作成・初期化するスクリプト
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_db_path() -> Path:
    """データベースパスを取得"""
    project_root = Path(__file__).parent.parent.parent
    return project_root / "data" / "household.db"


def create_expense_classification_table(conn: sqlite3.Connection) -> None:
    """支出分類テーブルを作成"""
    sql = """
    CREATE TABLE IF NOT EXISTS expense_classification (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analysis_period_start DATETIME NOT NULL,
        analysis_period_end DATETIME NOT NULL,
        category_major VARCHAR(100) NOT NULL,
        category_minor VARCHAR(100),
        classification VARCHAR(20) NOT NULL,
        confidence NUMERIC(5, 4) NOT NULL,
        iqr_analysis TEXT,
        occurrence_rate NUMERIC(5, 4),
        coefficient_of_variation NUMERIC(5, 4),
        outlier_count INTEGER,
        mean_amount NUMERIC(12, 2),
        std_amount NUMERIC(12, 2),
        occurrence_count INTEGER,
        total_months INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    logger.info("✅ Created expense_classification table")

    # インデックスを作成
    indexes = [
        """
        CREATE INDEX IF NOT EXISTS idx_expense_classification_period
        ON expense_classification(analysis_period_start, analysis_period_end)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_expense_classification_category
        ON expense_classification(category_major, category_minor)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_expense_classification_type
        ON expense_classification(classification)
        """,
    ]

    for idx_sql in indexes:
        cursor.execute(idx_sql)
    conn.commit()
    logger.info("✅ Created expense_classification indexes")


def create_fi_progress_cache_table(conn: sqlite3.Connection) -> None:
    """FIRE進捗キャッシュテーブルを作成"""
    sql = """
    CREATE TABLE IF NOT EXISTS fi_progress_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date DATETIME NOT NULL,
        data_period_end DATETIME NOT NULL,
        current_assets NUMERIC(15, 2) NOT NULL,
        annual_expense NUMERIC(15, 2) NOT NULL,
        fire_target NUMERIC(15, 2) NOT NULL,
        progress_rate NUMERIC(5, 2) NOT NULL,
        monthly_growth_rate NUMERIC(5, 4),
        growth_confidence NUMERIC(5, 4),
        data_points_used INTEGER,
        months_to_fi NUMERIC(7, 2),
        is_achievable INTEGER DEFAULT 1,
        projected_12m NUMERIC(15, 2),
        projected_60m NUMERIC(15, 2),
        analysis_method VARCHAR(50) DEFAULT 'regression',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """
    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    logger.info("✅ Created fi_progress_cache table")

    # インデックスを作成
    indexes = [
        """
        CREATE INDEX IF NOT EXISTS idx_fi_progress_snapshot_date
        ON fi_progress_cache(snapshot_date)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fi_progress_data_period_end
        ON fi_progress_cache(data_period_end)
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_fi_progress_created_at
        ON fi_progress_cache(created_at)
        """,
    ]

    for idx_sql in indexes:
        cursor.execute(idx_sql)
    conn.commit()
    logger.info("✅ Created fi_progress_cache indexes")


def create_fire_asset_snapshots_table(conn: sqlite3.Connection) -> None:
    """FIRE資産スナップショットテーブルを作成"""

    sql = """
    CREATE TABLE IF NOT EXISTS fire_asset_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date DATE NOT NULL UNIQUE,
        cash_and_deposits INTEGER NOT NULL DEFAULT 0,
        stocks_cash INTEGER NOT NULL DEFAULT 0,
        stocks_margin INTEGER NOT NULL DEFAULT 0,
        investment_trusts INTEGER NOT NULL DEFAULT 0,
        pension INTEGER NOT NULL DEFAULT 0,
        points INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """

    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    logger.info("✅ Created fire_asset_snapshots table")

    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_fire_snapshot_date
        ON fire_asset_snapshots(snapshot_date)
        """
    )
    conn.commit()
    logger.info("✅ Created fire_asset_snapshots index")


def drop_expense_classification_table(conn: sqlite3.Connection) -> None:
    """支出分類テーブルを削除（ロールバック用）"""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS expense_classification")
    conn.commit()
    logger.info("⚠️  Dropped expense_classification table")


def drop_fi_progress_cache_table(conn: sqlite3.Connection) -> None:
    """FIRE進捗キャッシュテーブルを削除（ロールバック用）"""
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS fi_progress_cache")
    conn.commit()
    logger.info("⚠️  Dropped fi_progress_cache table")


def drop_fire_asset_snapshots_table(conn: sqlite3.Connection) -> None:
    """FIRE資産スナップショットテーブルを削除（ロールバック用）"""

    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS fire_asset_snapshots")
    conn.commit()
    logger.info("⚠️  Dropped fire_asset_snapshots table")


def migrate_up(db_path: Path | None = None) -> None:
    """マイグレーションを実行（アップグレード）"""
    if db_path is None:
        db_path = get_db_path()

    logger.info("Migrating UP: %s", db_path)

    if not db_path.exists():
        logger.warning("Database file not found: %s", db_path)
        logger.info("Creating new database...")
        db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        conn = sqlite3.connect(str(db_path))
        create_expense_classification_table(conn)
        create_fi_progress_cache_table(conn)
        create_fire_asset_snapshots_table(conn)
        conn.close()
        logger.info("✅ Migration UP completed successfully")
    except sqlite3.Error as e:
        logger.error("❌ Migration failed: %s", e)
        raise


def migrate_down(db_path: Path | None = None) -> None:
    """マイグレーションを実行（ダウングレード）"""
    if db_path is None:
        db_path = get_db_path()

    logger.info("Migrating DOWN: %s", db_path)

    if not db_path.exists():
        logger.warning("Database file not found: %s", db_path)
        return

    try:
        conn = sqlite3.connect(str(db_path))
        drop_expense_classification_table(conn)
        drop_fi_progress_cache_table(conn)
        drop_fire_asset_snapshots_table(conn)
        conn.close()
        logger.info("✅ Migration DOWN completed successfully")
    except sqlite3.Error as e:
        logger.error("❌ Migration rollback failed: %s", e)
        raise


def verify_migration(db_path: Path | None = None) -> dict[str, bool]:
    """マイグレーション結果を検証"""
    if db_path is None:
        db_path = get_db_path()

    logger.info("Verifying migration: %s", db_path)

    result = {
        "expense_classification": False,
        "fi_progress_cache": False,
        "fire_asset_snapshots": False,
    }

    if not db_path.exists():
        logger.warning("Database file not found: %s", db_path)
        return result

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # expense_classificationテーブルの確認
        query1 = (
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='expense_classification'"
        )
        cursor.execute(query1)
        result["expense_classification"] = cursor.fetchone() is not None

        # fi_progress_cacheテーブルの確認
        query2 = (
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='fi_progress_cache'"
        )
        cursor.execute(query2)
        result["fi_progress_cache"] = cursor.fetchone() is not None

        # fire_asset_snapshotsテーブルの確認
        query3 = (
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='fire_asset_snapshots'"
        )
        cursor.execute(query3)
        result["fire_asset_snapshots"] = cursor.fetchone() is not None

        conn.close()

        for table_name, exists in result.items():
            status = "✅" if exists else "❌"
            exists_str = "exists" if exists else "not found"
            logger.info("%s Table '%s': %s", status, table_name, exists_str)

        return result
    except sqlite3.Error as e:
        logger.error("❌ Verification failed: %s", e)
        raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
    else:
        command = "up"

    if command == "up":
        migrate_up()
        verify_migration()
    elif command == "down":
        migrate_down()
        verify_migration()
    elif command == "verify":
        verify_migration()
    else:
        logger.error("Unknown command: %s", command)
        logger.info("Available commands: up, down, verify")
        sys.exit(1)
