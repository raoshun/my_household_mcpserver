"""Unit tests for DuplicateService."""

# flake8: noqa: F811

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from household_mcp.database.models import Base, DuplicateCheck, Transaction
from household_mcp.duplicate import DetectionOptions, DuplicateService


@pytest.fixture
def db_session():
    """Create a test database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_transactions(db_session: Session):
    """Create sample transactions for testing."""
    transactions = [
        Transaction(
            source_file="test.csv",
            row_number=1,
            date=datetime(2024, 1, 15),
            amount=Decimal("-5000.00"),
            description="スーパーマーケット A店",
            category_major="食費",
            category_minor="食料品",
            account="現金",
            is_duplicate=0,
        ),
        Transaction(
            source_file="test.csv",
            row_number=2,
            date=datetime(2024, 1, 15),
            amount=Decimal("-5000.00"),
            description="スーパーマーケット A店",
            category_major="食費",
            category_minor="食料品",
            account="クレジットカード",
            is_duplicate=0,
        ),
        Transaction(
            source_file="test.csv",
            row_number=3,
            date=datetime(2024, 1, 20),
            amount=Decimal("-3000.00"),
            description="レストラン B",
            category_major="食費",
            category_minor="外食",
            account="現金",
            is_duplicate=0,
        ),
    ]
    for trans in transactions:
        db_session.add(trans)
    db_session.commit()
    return transactions


def test_detect_and_save_candidates(db_session: Session, sample_transactions):
    """Test detecting and saving duplicate candidates."""
    service = DuplicateService(db_session)
    options = DetectionOptions(
        date_tolerance_days=0,
        amount_tolerance_abs=0.0,
        amount_tolerance_pct=0.0,
        min_similarity_score=0.8,
    )

    count = service.detect_and_save_candidates(options)

    assert count == 1  # 2つの完全一致取引から1つの候補

    # DuplicateCheckテーブルを確認
    checks = db_session.query(DuplicateCheck).all()
    assert len(checks) == 1
    assert checks[0].similarity_score >= 0.8
    assert checks[0].user_decision is None


def test_get_pending_candidates(db_session: Session, sample_transactions):
    """Test getting pending duplicate candidates."""
    service = DuplicateService(db_session)
    options = DetectionOptions(min_similarity_score=0.8)
    service.detect_and_save_candidates(options)

    candidates = service.get_pending_candidates(limit=10)

    assert len(candidates) == 1
    assert "check_id" in candidates[0]
    assert "transaction_1" in candidates[0]
    assert "transaction_2" in candidates[0]
    assert "similarity_score" in candidates[0]


def test_get_candidate_detail(db_session: Session, sample_transactions):
    """Test getting candidate detail."""
    service = DuplicateService(db_session)
    options = DetectionOptions(min_similarity_score=0.8)
    service.detect_and_save_candidates(options)

    # 最初のチェックIDを取得
    check = db_session.query(DuplicateCheck).first()
    detail = service.get_candidate_detail(check.id)

    assert detail is not None
    assert detail["check_id"] == check.id
    assert "transaction_1" in detail
    assert "transaction_2" in detail
    assert "similarity_score" in detail
    assert "detection_params" in detail


def test_get_candidate_detail_not_found(db_session: Session):
    """Test getting candidate detail for non-existent check_id."""
    service = DuplicateService(db_session)
    detail = service.get_candidate_detail(9999)

    assert detail is None


def test_confirm_duplicate_as_duplicate(db_session: Session, sample_transactions):
    """Test confirming a pair as duplicate."""
    service = DuplicateService(db_session)
    options = DetectionOptions(min_similarity_score=0.8)
    service.detect_and_save_candidates(options)

    check = db_session.query(DuplicateCheck).first()
    result = service.confirm_duplicate(check.id, "duplicate")

    assert result["success"] is True
    assert "marked_transaction_id" in result

    # 後の取引がis_duplicate=1になっているか確認
    marked_id = result["marked_transaction_id"]
    marked_trans = (
        db_session.query(Transaction).filter(Transaction.id == marked_id).first()
    )
    assert marked_trans.is_duplicate == 1
    assert marked_trans.duplicate_of is not None
    assert marked_trans.duplicate_checked == 1


def test_confirm_duplicate_as_not_duplicate(db_session: Session, sample_transactions):
    """Test confirming a pair as not duplicate."""
    service = DuplicateService(db_session)
    options = DetectionOptions(min_similarity_score=0.8)
    service.detect_and_save_candidates(options)

    check = db_session.query(DuplicateCheck).first()
    result = service.confirm_duplicate(check.id, "not_duplicate")

    assert result["success"] is True

    # 両方の取引がduplicate_checked=1になっているか確認
    trans1 = (
        db_session.query(Transaction)
        .filter(Transaction.id == check.transaction_id_1)
        .first()
    )
    trans2 = (
        db_session.query(Transaction)
        .filter(Transaction.id == check.transaction_id_2)
        .first()
    )
    assert trans1.duplicate_checked == 1
    assert trans2.duplicate_checked == 1
    assert trans1.is_duplicate == 0
    assert trans2.is_duplicate == 0


def test_confirm_duplicate_skip(db_session: Session, sample_transactions):
    """Test skipping duplicate decision."""
    service = DuplicateService(db_session)
    options = DetectionOptions(min_similarity_score=0.8)
    service.detect_and_save_candidates(options)

    check = db_session.query(DuplicateCheck).first()
    result = service.confirm_duplicate(check.id, "skip")

    assert result["success"] is True

    # user_decisionが"skip"になっているか確認
    updated_check = (
        db_session.query(DuplicateCheck).filter(DuplicateCheck.id == check.id).first()
    )
    assert updated_check.user_decision == "skip"


def test_restore_duplicate(db_session: Session, sample_transactions):
    """Test restoring a transaction marked as duplicate."""
    service = DuplicateService(db_session)
    options = DetectionOptions(min_similarity_score=0.8)
    service.detect_and_save_candidates(options)

    # 重複として確認
    check = db_session.query(DuplicateCheck).first()
    confirm_result = service.confirm_duplicate(check.id, "duplicate")
    marked_id = confirm_result["marked_transaction_id"]

    # 復元
    result = service.restore_duplicate(marked_id)

    assert result["success"] is True

    # 復元された取引を確認
    restored_trans = (
        db_session.query(Transaction).filter(Transaction.id == marked_id).first()
    )
    assert restored_trans.is_duplicate == 0
    assert restored_trans.duplicate_of is None
    assert restored_trans.duplicate_checked == 0


def test_restore_duplicate_not_marked(db_session: Session, sample_transactions):
    """Test restoring a transaction not marked as duplicate."""
    service = DuplicateService(db_session)
    result = service.restore_duplicate(sample_transactions[0].id)

    assert result["success"] is False
    assert "マークされていません" in result["message"]


def test_get_stats(db_session: Session, sample_transactions):
    """Test getting duplicate detection statistics."""
    service = DuplicateService(db_session)
    options = DetectionOptions(min_similarity_score=0.8)
    service.detect_and_save_candidates(options)

    # 1つを重複として確認
    check = db_session.query(DuplicateCheck).first()
    service.confirm_duplicate(check.id, "duplicate")

    stats = service.get_stats()

    assert stats["total_transactions"] == 3
    assert stats["duplicate_transactions"] == 1
    assert stats["total_checks"] == 1
    assert stats["pending_checks"] == 0
    assert stats["confirmed_duplicate"] == 1
    assert stats["confirmed_not_duplicate"] == 0
    assert stats["skipped"] == 0


def test_multiple_detection_runs(db_session: Session, sample_transactions):
    """Test that multiple detection runs don't create duplicate checks."""
    service = DuplicateService(db_session)
    options = DetectionOptions(min_similarity_score=0.8)

    # 1回目の検出
    count1 = service.detect_and_save_candidates(options)
    checks_after_first = db_session.query(DuplicateCheck).count()

    # 2回目の検出（既に保存済みなので新規保存は0件）
    count2 = service.detect_and_save_candidates(options)
    checks_after_second = db_session.query(DuplicateCheck).count()

    # 1回目で検出された数と、チェックテーブルの件数が一致
    assert count1 == 1
    assert checks_after_first == 1
    # 2回目は新規保存なし
    assert count2 == 0
    # チェックテーブルの件数は変わらない
    assert checks_after_second == checks_after_first
