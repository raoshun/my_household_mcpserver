#!/usr/bin/env python3
"""家計簿MCPサーバーのテストスクリプト.

サーバーの主要機能をテストします
"""

import os
import sys

# パスの設定
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))


def test_server_import():
    """サーバーモジュールの読み込みテスト."""
    try:
        from household_mcp.server import app as _

        print("✅ サーバーモジュールの読み込み成功")
        return True
    except Exception as e:
        print(f"❌ サーバーモジュールの読み込み失敗: {e}")
        return False


def test_database_models():
    """データベースモデルのテスト."""
    try:
        from datetime import date
        from decimal import Decimal

        from household_mcp.database.models import Account, Transaction

        # Transaction作成テスト
        _ = Transaction(
            amount=Decimal("1000"),
            description="テスト取引",
            type="expense",
            date=date.today(),
        )
        print("✅ Transactionモデルの作成成功")

        # Account作成テスト
        _ = Account(
            name="テストアカウント", type="bank", initial_balance=Decimal("10000")
        )
        print("✅ Accountモデルの作成成功")

        return True
    except Exception as e:
        print(f"❌ データベースモデルのテスト失敗: {e}")
        return False


def test_database_connection():
    """データベース接続のテスト."""
    try:
        from household_mcp.database.connection import get_database_connection

        db_conn = get_database_connection("test_household.db")
        with db_conn:
            print("✅ データベース接続成功")

        # テストファイルの削除
        if os.path.exists("test_household.db"):
            os.remove("test_household.db")

        return True
    except Exception as e:
        print(f"❌ データベース接続のテスト失敗: {e}")
        return False


def test_migration_manager():
    """マイグレーション管理のテスト."""
    try:
        from household_mcp.database.migrations import create_migration_manager

        migration_manager = create_migration_manager("test_migration.db")
        status = migration_manager.get_migration_status()

        print("✅ マイグレーション管理テスト成功")
        print(f"   - 利用可能マイグレーション: {status['total_migrations']}")
        print(f"   - 適用済み: {status['applied_count']}")
        print(f"   - 未適用: {status['pending_count']}")

        # テストファイルの削除
        if os.path.exists("test_migration.db"):
            os.remove("test_migration.db")

        return True
    except Exception as e:
        print(f"❌ マイグレーション管理のテスト失敗: {e}")
        return False


def main():
    """メインテスト関数."""
    print("=== 家計簿MCPサーバー テスト開始 ===\n")

    tests = [
        ("サーバーモジュール読み込み", test_server_import),
        ("データベースモデル", test_database_models),
        ("データベース接続", test_database_connection),
        ("マイグレーション管理", test_migration_manager),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"📋 {test_name}テスト実行中...")
        result = test_func()
        results.append(result)
        print()

    # 結果まとめ
    passed = sum(results)
    total = len(results)

    print("=== テスト結果まとめ ===")
    print(f"成功: {passed}/{total}")

    if passed == total:
        print("🎉 すべてのテストが成功しました！")
        return 0
    else:
        print("⚠️  一部のテストが失敗しました")
        return 1


if __name__ == "__main__":
    sys.exit(main())
