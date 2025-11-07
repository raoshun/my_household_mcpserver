#!/usr/bin/env python
"""Database initialization and migration script for Phase 13."""

import logging
import sys

from household_mcp.database import CSVImporter, DatabaseManager

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def initialize_and_migrate() -> None:
    """Database initialization and CSV migration."""
    logger.info("=" * 80)
    logger.info("フェーズ 13: SQLite データベース初期化 & CSV マイグレーション開始")
    logger.info("=" * 80)

    # Step 1: DatabaseManager 初期化
    logger.info("\nステップ 1: DatabaseManager 初期化")
    db_manager = DatabaseManager(db_path="data/household.db")

    try:
        # データベースが既に存在するか確認
        if db_manager.database_exists():
            logger.warning("⚠️  データベースファイルが既に存在します: data/household.db")
            logger.info("既存データベースを使用します")
        else:
            logger.info("✅ 新規データベースファイルを作成します")

        # Step 2: スキーマ初期化（テーブル作成）
        logger.info("\nステップ 2: テーブル作成")
        db_manager.initialize_database()
        logger.info("✅ テーブル作成完了")
        logger.info("  - Transaction（取引データ）")
        logger.info("  - DuplicateCheck（重複検出履歴）")
        logger.info("  - AssetClass（資産分類定義）")
        logger.info("  - AssetRecord（資産レコード）")
        logger.info("  - ExpenseClassification（支出分類）")
        logger.info("  - FIProgressCache（FIRE進捗スナップショット）")

        # Step 3: CSV マイグレーション
        logger.info("\nステップ 3: CSV → SQLite マイグレーション")
        logger.info("対象: data/収入・支出詳細_*.csv")

        with db_manager.session_scope() as session:
            importer = CSVImporter(session)
            result = importer.import_all_csvs(data_dir="data")

            files_processed = result["files_processed"]
            total_imported = result["total_imported"]
            total_skipped = result["total_skipped"]
            errors = result["errors"]

            logger.info("✅ マイグレーション完了")
            logger.info("  - 処理ファイル数: %s", files_processed)
            logger.info("  - インポート件数: %s", f"{total_imported:,}")
            logger.info("  - スキップ件数（既存重複）: %s", f"{total_skipped:,}")

            if errors:
                logger.warning("⚠️  エラー件数: %s", len(errors))
                for error in errors[:5]:  # 最初の5件のみ表示
                    logger.warning("    - %s", error)
                if len(errors) > 5:
                    logger.warning("    ... 他 %s 件", len(errors) - 5)

        logger.info("=" * 80)
        logger.info("✅ フェーズ 13 初期化・マイグレーション完了")
        logger.info("=" * 80)
        logger.info("\n次のステップ:")
        logger.info("  1. TASK-1303: 取引 CRUD API 実装")
        logger.info("  2. TASK-1304: 資産 CRUD API 実装")
        logger.info("  3. TASK-1305: 互換性レイヤー実装")

    except (OSError, ValueError, TypeError) as e:
        logger.error("❌ エラーが発生しました: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        db_manager.close()


if __name__ == "__main__":
    initialize_and_migrate()
