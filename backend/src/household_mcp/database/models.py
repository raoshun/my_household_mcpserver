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


class AssetClass(Base):
    """資産クラス定義テーブル."""

    __tablename__ = "assets_classes"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 資産クラス情報
    name = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String(10), nullable=True)

    # メタ情報
    created_at = Column(DateTime, default=datetime.now)

    # リレーション
    records = relationship("AssetRecord", back_populates="asset_class")

    def __repr__(self) -> str:
        """文字列表現."""
        return (
            f"<AssetClass(id={self.id}, name={self.name}, "
            f"display_name={self.display_name})>"
        )


class AssetRecord(Base):
    """資産レコードテーブル."""

    __tablename__ = "asset_records"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 資産データ
    record_date = Column(DateTime, nullable=False, index=True)
    asset_class_id = Column(Integer, ForeignKey("assets_classes.id"), nullable=False)
    sub_asset_name = Column(String(255), nullable=False)
    amount = Column(Integer, nullable=False)  # JPY単位
    memo = Column(Text, nullable=True)

    # 管理フラグ
    is_deleted = Column(Integer, default=0, index=True)
    is_manual = Column(Integer, default=1)
    # 'manual', 'linked', 'calculated'
    source_type = Column(String(50), default="manual")
    linked_transaction_id = Column(Integer, nullable=True)

    # メタ情報
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    created_by = Column(String(100), default="user")

    # リレーション
    asset_class = relationship("AssetClass", back_populates="records")

    # テーブル制約
    __table_args__ = (
        Index("idx_asset_records_date", "record_date"),
        Index("idx_asset_records_class", "asset_class_id"),
        Index("idx_asset_records_is_deleted", "is_deleted"),
        Index("idx_asset_records_date_class", "record_date", "asset_class_id"),
    )

    def __repr__(self) -> str:
        """文字列表現."""
        return (
            f"<AssetRecord(id={self.id}, record_date={self.record_date}, "
            f"asset_class_id={self.asset_class_id}, amount={self.amount})>"
        )


class ExpenseClassification(Base):
    """支出分類結果テーブル（定期/不定期分類と信頼度）."""

    __tablename__ = "expense_classification"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 分類対象期間
    analysis_period_start = Column(DateTime, nullable=False, index=True)
    analysis_period_end = Column(DateTime, nullable=False, index=True)

    # 支出カテゴリ
    category_major = Column(String(100), nullable=False)
    category_minor = Column(String(100), nullable=True)

    # 分類結果
    classification = Column(String(20), nullable=False)  # regular/irregular
    confidence = Column(Numeric(5, 4), nullable=False)  # 0.0-1.0

    # 分析指標
    iqr_analysis = Column(Text, nullable=True)  # JSON形式
    occurrence_rate = Column(Numeric(5, 4), nullable=True)
    coefficient_of_variation = Column(Numeric(5, 4), nullable=True)
    outlier_count = Column(Integer, nullable=True)

    # 統計量
    mean_amount = Column(Numeric(12, 2), nullable=True)
    std_amount = Column(Numeric(12, 2), nullable=True)
    occurrence_count = Column(Integer, nullable=True)
    total_months = Column(Integer, nullable=True)

    # メタ情報
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # テーブル制約
    __table_args__ = (
        Index(
            "idx_expense_classification_period",
            "analysis_period_start",
            "analysis_period_end",
        ),
        Index(
            "idx_expense_classification_category",
            "category_major",
            "category_minor",
        ),
        Index("idx_expense_classification_type", "classification"),
    )

    def __repr__(self) -> str:
        """文字列表現."""
        return (
            f"<ExpenseClassification(id={self.id}, "
            f"category={self.category_major}, "
            f"classification={self.classification}, "
            f"confidence={self.confidence})>"
        )


class FIProgressCache(Base):
    """FIRE進捗スナップショットキャッシュテーブル."""

    __tablename__ = "fi_progress_cache"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # スナップショット期間
    snapshot_date = Column(DateTime, nullable=False, index=True)
    data_period_end = Column(DateTime, nullable=False, index=True)

    # FIRE指標
    current_assets = Column(Numeric(15, 2), nullable=False)
    annual_expense = Column(Numeric(15, 2), nullable=False)
    fire_target = Column(Numeric(15, 2), nullable=False)
    progress_rate = Column(Numeric(5, 2), nullable=False)  # 0-999+

    # 成長率分析
    monthly_growth_rate = Column(Numeric(5, 4), nullable=True)  # 小数形式
    growth_confidence = Column(Numeric(5, 4), nullable=True)  # 0.0-1.0
    data_points_used = Column(Integer, nullable=True)

    # 達成予測
    months_to_fi = Column(Numeric(7, 2), nullable=True)  # NULLの場合は達成不可能
    is_achievable = Column(Integer, default=1)  # 0: 達成不可能, 1: 達成可能

    # シナリオ投影（12ヶ月後、60ヶ月後）
    projected_12m = Column(Numeric(15, 2), nullable=True)
    projected_60m = Column(Numeric(15, 2), nullable=True)

    # メタ情報
    analysis_method = Column(String(50), default="regression")
    created_at = Column(DateTime, default=datetime.now)

    # テーブル制約
    __table_args__ = (
        Index("idx_fi_progress_snapshot_date", "snapshot_date"),
        Index("idx_fi_progress_data_period_end", "data_period_end"),
        Index("idx_fi_progress_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        """文字列表現."""
        return (
            f"<FIProgressCache(id={self.id}, "
            f"snapshot_date={self.snapshot_date}, "
            f"progress_rate={self.progress_rate}, "
            f"months_to_fi={self.months_to_fi})>"
        )


class Budget(Base):
    """予算管理テーブル."""

    __tablename__ = "budgets"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # 予算期間
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=False, index=True)

    # カテゴリ
    category_major = Column(String(100), nullable=False, index=True)
    category_minor = Column(String(100))

    # 予算額
    amount = Column(Numeric(12, 2), nullable=False)

    # メタ情報
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    # テーブル制約
    __table_args__ = (
        Index("idx_budget_period", "year", "month"),
        Index("idx_budget_category", "category_major", "category_minor"),
    )

    def __repr__(self) -> str:
        """文字列表現."""
        return (
            f"<Budget(id={self.id}, "
            f"year={self.year}, "
            f"month={self.month}, "
            f"category={self.category_major}, "
            f"amount={self.amount})>"
        )
