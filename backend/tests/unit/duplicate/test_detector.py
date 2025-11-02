"""Unit tests for DuplicateDetector.

NOTE: These tests require the 'db' extra (sqlalchemy).
They are skipped automatically when sqlalchemy is unavailable.
"""

import os
import tempfile
from datetime import datetime
from decimal import Decimal

import pytest

# Optional db dependencies
try:
    from household_mcp.database import DatabaseManager, Transaction
    from household_mcp.duplicate import DetectionOptions, DuplicateDetector

    HAS_DB = True
except Exception:
    HAS_DB = False
    DatabaseManager = None  # type: ignore[assignment]
    Transaction = None  # type: ignore[assignment]
    DetectionOptions = None  # type: ignore[assignment]
    DuplicateDetector = None  # type: ignore[assignment]

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
def sample_transactions(db_manager):  # type: ignore[no-untyped-def]
    """テスト用のサンプル取引データを作成."""
    with db_manager.session_scope() as session:
        # 完全重複（同じ日付・同じ金額）
        trans1 = Transaction(
            source_file="file1.csv",
            row_number=1,
            date=datetime(2025, 1, 15),
            amount=Decimal("1000.00"),
            description="スーパー",
            category_major="食費",
            is_duplicate=0,
        )
        trans2 = Transaction(
            source_file="file2.csv",
            row_number=1,
            date=datetime(2025, 1, 15),
            amount=Decimal("1000.00"),
            description="スーパー",
            category_major="食費",
            is_duplicate=0,
        )

        # 日付が1日ずれている
        trans3 = Transaction(
            source_file="file1.csv",
            row_number=2,
            date=datetime(2025, 1, 20),
            amount=Decimal("500.00"),
            description="コンビニ",
            category_major="食費",
            is_duplicate=0,
        )
        trans4 = Transaction(
            source_file="file2.csv",
            row_number=2,
            date=datetime(2025, 1, 21),
            amount=Decimal("500.00"),
            description="コンビニ",
            category_major="食費",
            is_duplicate=0,
        )

        # 金額が異なる（重複ではない）
        trans5 = Transaction(
            source_file="file1.csv",
            row_number=3,
            date=datetime(2025, 1, 25),
            amount=Decimal("2000.00"),
            description="レストラン",
            category_major="食費",
            is_duplicate=0,
        )
        trans6 = Transaction(
            source_file="file2.csv",
            row_number=3,
            date=datetime(2025, 1, 25),
            amount=Decimal("3000.00"),
            description="レストラン",
            category_major="食費",
            is_duplicate=0,
        )

        session.add_all([trans1, trans2, trans3, trans4, trans5, trans6])
        session.commit()

        # IDを返す
        return [trans1.id, trans2.id, trans3.id, trans4.id, trans5.id, trans6.id]


def test_detect_exact_duplicates(db_manager, sample_transactions):  # type: ignore[no-untyped-def]
    """完全一致の重複検出テスト."""
    with db_manager.session_scope() as session:
        # デフォルトオプション（完全一致のみ）
        detector = DuplicateDetector(session)
        candidates = detector.detect_duplicates()

        # trans1 と trans2 が検出されるべき
        assert len(candidates) >= 1

        # 最初の候補を検証
        trans1, trans2, score = candidates[0]
        assert trans1.date == trans2.date
        assert trans1.amount == trans2.amount
        assert score >= 0.8


def test_detect_with_date_tolerance(db_manager, sample_transactions):  # type: ignore[no-untyped-def]
    """日付誤差許容ありの重複検出テスト."""
    with db_manager.session_scope() as session:
        # 日付誤差1日まで許容
        options = DetectionOptions(date_tolerance_days=1, min_similarity_score=0.7)
        detector = DuplicateDetector(session, options)
        candidates = detector.detect_duplicates()

        # trans1-trans2 と trans3-trans4 が検出されるべき
        assert len(candidates) >= 2

        # trans3-trans4 のペアを検証
        found_date_tolerance_pair = False
        for t1, t2, score in candidates:
            date_diff = abs((t1.date - t2.date).days)
            if date_diff == 1 and t1.amount == t2.amount:
                found_date_tolerance_pair = True
                assert score >= 0.7

        assert found_date_tolerance_pair


def test_detect_with_amount_tolerance(db_manager):  # type: ignore[no-untyped-def]
    """金額誤差許容ありの重複検出テスト."""
    with db_manager.session_scope() as session:
        # 近い金額のデータを作成
        trans1 = Transaction(
            source_file="file1.csv",
            row_number=1,
            date=datetime(2025, 2, 1),
            amount=Decimal("1000.00"),
            description="買い物",
            is_duplicate=0,
        )
        trans2 = Transaction(
            source_file="file2.csv",
            row_number=1,
            date=datetime(2025, 2, 1),
            amount=Decimal("1050.00"),  # 50円の差
            description="買い物",
            is_duplicate=0,
        )
        session.add_all([trans1, trans2])
        session.commit()

        # 金額絶対誤差100円まで許容
        options = DetectionOptions(amount_tolerance_abs=100.0, min_similarity_score=0.7)
        detector = DuplicateDetector(session, options)
        candidates = detector.detect_duplicates()

        # 検出されるべき
        assert len(candidates) >= 1
        t1, t2, score = candidates[0]
        assert abs(float(t1.amount) - float(t2.amount)) <= 100


def test_no_detection_for_different_amounts(db_manager, sample_transactions):  # type: ignore[no-untyped-def]
    """金額が異なる場合は検出されないことを確認."""
    with db_manager.session_scope() as session:
        detector = DuplicateDetector(session)
        candidates = detector.detect_duplicates()

        # trans5-trans6（金額が異なる）は検出されないべき
        for t1, t2, _score in candidates:
            # 両方とも同じ日付の場合、金額は同じであるべき
            if t1.date == t2.date:
                assert t1.amount == t2.amount


def test_exclude_already_duplicate(db_manager):  # type: ignore[no-untyped-def]
    """既に重複フラグが立っている取引は除外されることを確認."""
    with db_manager.session_scope() as session:
        trans1 = Transaction(
            source_file="file1.csv",
            row_number=1,
            date=datetime(2025, 3, 1),
            amount=Decimal("1000.00"),
            description="テスト",
            is_duplicate=1,  # 既に重複
        )
        trans2 = Transaction(
            source_file="file2.csv",
            row_number=1,
            date=datetime(2025, 3, 1),
            amount=Decimal("1000.00"),
            description="テスト",
            is_duplicate=0,
        )
        session.add_all([trans1, trans2])
        session.commit()

        detector = DuplicateDetector(session)
        candidates = detector.detect_duplicates()

        # trans1は除外されるため検出されない
        for t1, t2, _score in candidates:
            assert t1.is_duplicate == 0
            assert t2.is_duplicate == 0


def test_similarity_score_calculation(db_manager):  # type: ignore[no-untyped-def]
    """類似度スコア計算の妥当性テスト."""
    with db_manager.session_scope() as session:
        # 完全一致
        trans1 = Transaction(
            source_file="file1.csv",
            row_number=1,
            date=datetime(2025, 4, 1),
            amount=Decimal("1000.00"),
            description="完全一致",
            is_duplicate=0,
        )
        trans2 = Transaction(
            source_file="file2.csv",
            row_number=1,
            date=datetime(2025, 4, 1),
            amount=Decimal("1000.00"),
            description="完全一致",
            is_duplicate=0,
        )
        session.add_all([trans1, trans2])
        session.commit()

        detector = DuplicateDetector(session)
        candidates = detector.detect_duplicates()

        # 完全一致のスコアは1.0に近いべき
        assert len(candidates) == 1
        t1, t2, score = candidates[0]
        assert score >= 0.95


def test_detect_with_transaction_ids(db_manager, sample_transactions):  # type: ignore[no-untyped-def]
    """特定の取引IDのみを対象とした検出テスト."""
    with db_manager.session_scope() as session:
        # 最初の2つのIDのみを指定
        target_ids = sample_transactions[:2]
        detector = DuplicateDetector(session)
        candidates = detector.detect_duplicates(transaction_ids=target_ids)

        # 指定したID内での検出のみ行われる
        for t1, t2, _score in candidates:
            assert t1.id in target_ids or t2.id in target_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
