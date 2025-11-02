"""Unit tests for CSVImporter.

NOTE: These tests require the 'db' extra to be installed.
They are skipped automatically in environments without SQLAlchemy.
"""

import os
import tempfile
from decimal import Decimal

import pandas as pd
import pytest

# Check if database dependencies are available
try:
    from household_mcp.database import CSVImporter, DatabaseManager, Transaction

    HAS_DB = True
except ImportError:
    HAS_DB = False
    CSVImporter = None  # type: ignore[assignment]
    DatabaseManager = None  # type: ignore[assignment]
    Transaction = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(not HAS_DB, reason="requires db extras (sqlalchemy)")


@pytest.fixture
def db_manager():  # type: ignore[no-untyped-def]
    """テスト用のデータベースマネージャを作成."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        manager = DatabaseManager(db_path=db_path)
        manager.initialize_database()
        yield manager
        manager.close()


@pytest.fixture
def sample_csv(tmp_path):  # type: ignore[no-untyped-def]
    """サンプルCSVファイルを作成."""
    csv_path = tmp_path / "収入・支出詳細_2025-01-01_2025-01-31.csv"

    data = {
        "日付": ["2025-01-01", "2025-01-02", "2025-01-03"],
        "金額（円）": [1000, -500, 2000],  # 全角括弧
        "内容": ["給与", "食費", "ボーナス"],
        "大項目": ["収入", "食費", "収入"],
        "中項目": ["給与", "外食", "賞与"],
        "口座": ["銀行A", "クレジットカード", "銀行A"],
        "メモ": ["", "ランチ", ""],
        "計算対象": [1, 1, 1],
    }

    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False, encoding="cp932")

    return csv_path


def test_import_single_csv(db_manager, sample_csv):  # type: ignore[no-untyped-def]
    """単一CSVファイルのインポートテスト."""
    with db_manager.session_scope() as session:
        importer = CSVImporter(session)
        result = importer.import_csv(str(sample_csv))

        # 結果検証
        assert result["imported"] == 3
        assert result["skipped"] == 0
        assert len(result["errors"]) == 0

        # データベース検証
        transactions = session.query(Transaction).all()
        assert len(transactions) == 3

        # 最初のレコード検証
        first_trans = transactions[0]
        assert first_trans.source_file == "収入・支出詳細_2025-01-01_2025-01-31.csv"
        assert first_trans.row_number == 0
        assert first_trans.amount == Decimal("1000")
        assert first_trans.description == "給与"
        assert first_trans.category_major == "収入"
        assert first_trans.is_duplicate == 0


def test_import_duplicate_prevention(db_manager, sample_csv):  # type: ignore[no-untyped-def]
    """重複インポート防止テスト."""
    with db_manager.session_scope() as session:
        importer = CSVImporter(session)

        # 1回目のインポート
        result1 = importer.import_csv(str(sample_csv))
        assert result1["imported"] == 3
        assert result1["skipped"] == 0

    # 新しいセッションで2回目のインポート
    with db_manager.session_scope() as session:
        importer = CSVImporter(session)
        result2 = importer.import_csv(str(sample_csv))

        # 全てスキップされる
        assert result2["imported"] == 0
        assert result2["skipped"] == 3
        assert len(result2["errors"]) == 0

        # データベース内は3件のまま
        transactions = session.query(Transaction).all()
        assert len(transactions) == 3


def test_import_invalid_csv(db_manager, tmp_path):  # type: ignore[no-untyped-def]
    """不正なCSVファイルのエラーハンドリングテスト."""
    invalid_csv = tmp_path / "invalid.csv"
    # 必須カラムが欠けているCSV
    invalid_csv.write_text("wrong_column\nvalue1\nvalue2", encoding="utf-8")

    with db_manager.session_scope() as session:
        importer = CSVImporter(session)
        result = importer.import_csv(str(invalid_csv))

        # エラーが記録される（日付や金額カラムがない）
        assert result["imported"] == 0
        assert len(result["errors"]) > 0


def test_import_all_csvs(db_manager, tmp_path):  # type: ignore[no-untyped-def]
    """複数CSVファイルの一括インポートテスト."""
    # 複数のCSVファイルを作成
    for month in range(1, 4):
        csv_path = tmp_path / f"収入・支出詳細_2025-0{month}-01_2025-0{month}-31.csv"
        data = {
            "日付": [f"2025-0{month}-01", f"2025-0{month}-02"],
            "金額（円）": [1000 * month, -500 * month],  # 全角括弧
            "内容": ["収入", "支出"],
            "大項目": ["収入", "食費"],
            "中項目": ["給与", "外食"],
            "口座": ["銀行A", "クレジット"],
            "メモ": ["", ""],
            "計算対象": [1, 1],
        }
        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False, encoding="cp932")

    # 一括インポート
    with db_manager.session_scope() as session:
        importer = CSVImporter(session)
        result = importer.import_all_csvs(str(tmp_path))

        # 結果検証
        assert result["files_processed"] == 3
        assert result["total_imported"] == 6  # 3ファイル × 2レコード
        assert result["total_skipped"] == 0
        assert len(result["errors"]) == 0

        # データベース検証
        transactions = session.query(Transaction).all()
        assert len(transactions) == 6


def test_import_with_missing_columns(db_manager, tmp_path):  # type: ignore[no-untyped-def]
    """欠損カラムを含むCSVのインポートテスト."""
    csv_path = tmp_path / "収入・支出詳細_2025-01-01_2025-01-31.csv"

    # 最小限のカラムのみ
    data = {
        "日付": ["2025-01-01"],
        "金額（円）": [1000],  # 全角括弧
    }

    df = pd.DataFrame(data)
    df.to_csv(csv_path, index=False, encoding="cp932")

    with db_manager.session_scope() as session:
        importer = CSVImporter(session)
        result = importer.import_csv(str(csv_path))

        # インポート成功（欠損はデフォルト値）
        assert result["imported"] == 1
        assert result["skipped"] == 0

        # データ検証
        trans = session.query(Transaction).first()
        assert trans.description == ""
        assert trans.category_major == ""
        assert trans.memo == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
