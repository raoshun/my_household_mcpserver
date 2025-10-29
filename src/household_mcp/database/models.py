"""SQLAlchemy models for household database."""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """ベースクラス."""

    pass


class Transaction(Base):
    """取引データのキャッシュテーブル."""

    __tablename__ = "transactions"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 元データ
    source_file = Column(String(255), nullable=False)
    row_number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text)
    category_major = Column(String(100))
    category_minor = Column(String(100))
    account = Column(String(100))
    memo = Column(Text)
    is_target = Column(Integer, default=1)

    # 重複管理フィールド
    is_duplicate = Column(Integer, default=0, index=True)
    duplicate_of = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    duplicate_checked = Column(Integer, default=0)
    duplicate_checked_at = Column(DateTime, nullable=True)

    # メタ情報
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # リレーション
    original_transaction = relationship(
        "Transaction", remote_side=[id], back_populates="duplicates"
    )
    duplicates = relationship(
        "Transaction", back_populates="original_transaction", remote_side=[duplicate_of]
    )

    duplicate_checks_as_1 = relationship(
        "DuplicateCheck",
        foreign_keys="DuplicateCheck.transaction_id_1",
        back_populates="transaction_1",
    )
    duplicate_checks_as_2 = relationship(
        "DuplicateCheck",
        foreign_keys="DuplicateCheck.transaction_id_2",
        back_populates="transaction_2",
    )

    # テーブル制約
    __table_args__ = (
        Index("idx_source_file_row", "source_file", "row_number", unique=True),
        Index("idx_date_amount", "date", "amount"),
        Index("idx_date_range", "date"),
    )

    def __repr__(self) -> str:
        """文字列表現."""
        return (
            f"<Transaction(id={self.id}, date={self.date}, "
            f"amount={self.amount}, is_duplicate={self.is_duplicate})>"
        )


class DuplicateCheck(Base):
    """重複検出履歴テーブル."""

    __tablename__ = "duplicate_checks"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 取引ID
    transaction_id_1 = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    transaction_id_2 = Column(Integer, ForeignKey("transactions.id"), nullable=False)

    # 検出パラメータ
    detection_date_tolerance = Column(Integer, nullable=True)
    detection_amount_tolerance_abs = Column(Numeric(12, 2), nullable=True)
    detection_amount_tolerance_pct = Column(Numeric(5, 2), nullable=True)

    # 検出結果
    similarity_score = Column(Numeric(5, 4), nullable=True)
    detected_at = Column(DateTime, default=datetime.now)

    # ユーザー判定
    user_decision = Column(String(20), nullable=True)
    decided_at = Column(DateTime, nullable=True)

    # リレーション
    transaction_1 = relationship(
        "Transaction",
        foreign_keys=[transaction_id_1],
        back_populates="duplicate_checks_as_1",
    )
    transaction_2 = relationship(
        "Transaction",
        foreign_keys=[transaction_id_2],
        back_populates="duplicate_checks_as_2",
    )

    # テーブル制約
    __table_args__ = (
        Index(
            "idx_transaction_pair", "transaction_id_1", "transaction_id_2", unique=True
        ),
        Index("idx_user_decision", "user_decision"),
    )

    def __repr__(self) -> str:
        """文字列表現."""
        return (
            f"<DuplicateCheck(id={self.id}, "
            f"t1={self.transaction_id_1}, t2={self.transaction_id_2}, "
            f"decision={self.user_decision})>"
        )
