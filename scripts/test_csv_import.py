"""CSVImporter integration test script."""

import sys  # noqa: E402
from pathlib import Path  # noqa: E402

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from household_mcp.database import CSVImporter, DatabaseManager  # noqa: E402


def main() -> None:
    """CSVインポートの統合テスト."""
    print("🚀 CSVImporter 統合テスト開始")
    print("-" * 60)

    # データベースマネージャ初期化
    db_path = "data/household.db"
    print(f"📁 データベース: {db_path}")

    manager = DatabaseManager(db_path=db_path)
    manager.initialize_database()
    print("✅ データベース初期化完了")

    # CSVインポート
    with manager.session_scope() as session:
        importer = CSVImporter(session)

        print("\n📥 CSVファイル一括インポート開始...")
        result = importer.import_all_csvs("data")

        print("\n📊 インポート結果:")
        print(f"  処理ファイル数: {result['files_processed']}")
        print(f"  インポート件数: {result['total_imported']}")
        print(f"  スキップ件数: {result['total_skipped']}")
        print(f"  エラー件数: {len(result['errors'])}")

        if result["errors"]:
            print("\n⚠️  エラー詳細:")
            for error in result["errors"][:5]:  # 最初の5件のみ表示
                print(f"    - {error}")

    # データ確認
    with manager.session_scope() as session:
        from household_mcp.database import Transaction

        total_count = session.query(Transaction).count()
        print(f"\n✅ データベース内の総取引数: {total_count}")

        # サンプルデータ表示
        sample = session.query(Transaction).limit(3).all()
        print("\n📋 サンプルデータ (最初の3件):")
        for trans in sample:
            print(
                f"  - {trans.date.date()} | {trans.amount:>10} 円 | {trans.description[:20]}"
            )

    manager.close()
    print("\n🎉 統合テスト完了!")


if __name__ == "__main__":
    main()
