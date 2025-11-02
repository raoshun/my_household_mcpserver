"""Duplicate resolution service for household MCP server."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from household_mcp.database.models import DuplicateCheck, Transaction
from household_mcp.duplicate import DetectionOptions, DuplicateDetector


class DuplicateService:
    """重複検出・解決サービス."""

    def __init__(self, db_session: Session):
        """
        初期化.

        Args:
            db_session: SQLAlchemy セッション

        """
        self.db = db_session

    def detect_and_save_candidates(
        self, options: DetectionOptions | None = None
    ) -> int:
        """
        重複候補を検出してDBに保存.

        Args:
            options: 検出オプション

        Returns:
            保存された候補数

        """
        detector = DuplicateDetector(self.db, options)
        candidates = detector.detect_duplicates()

        saved_count = 0
        for trans1, trans2, score in candidates:
            # 既存チェックがないか確認
            existing = (
                self.db.query(DuplicateCheck)
                .filter(
                    DuplicateCheck.transaction_id_1 == trans1.id,
                    DuplicateCheck.transaction_id_2 == trans2.id,
                )
                .first()
            )

            if not existing:
                check = DuplicateCheck(
                    transaction_id_1=trans1.id,
                    transaction_id_2=trans2.id,
                    detection_date_tolerance=(
                        options.date_tolerance_days if options else 0
                    ),
                    detection_amount_tolerance_abs=(
                        Decimal(str(options.amount_tolerance_abs))
                        if options
                        else Decimal("0")
                    ),
                    detection_amount_tolerance_pct=(
                        Decimal(str(options.amount_tolerance_pct))
                        if options
                        else Decimal("0")
                    ),
                    similarity_score=Decimal(str(score)),
                    detected_at=datetime.now(),
                )
                self.db.add(check)
                saved_count += 1

        self.db.commit()
        return saved_count

    def get_pending_candidates(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        未判定の重複候補を取得.

        Args:
            limit: 最大取得件数

        Returns:
            候補リスト

        """
        checks = (
            self.db.query(DuplicateCheck)
            .filter(DuplicateCheck.user_decision.is_(None))
            .order_by(DuplicateCheck.similarity_score.desc())
            .limit(limit)
            .all()
        )

        results = []
        for check in checks:
            trans1 = check.transaction_1
            trans2 = check.transaction_2

            date_diff = abs((trans1.date - trans2.date).days)
            amount_diff = abs(float(trans1.amount) - float(trans2.amount))

            results.append(
                {
                    "check_id": check.id,
                    "transaction_1": {
                        "id": trans1.id,
                        "date": trans1.date.strftime("%Y-%m-%d"),
                        "amount": float(trans1.amount),
                        "description": trans1.description or "",
                        "category": trans1.category_major or "",
                    },
                    "transaction_2": {
                        "id": trans2.id,
                        "date": trans2.date.strftime("%Y-%m-%d"),
                        "amount": float(trans2.amount),
                        "description": trans2.description or "",
                        "category": trans2.category_major or "",
                    },
                    "similarity_score": float(check.similarity_score),
                    "date_diff_days": date_diff,
                    "amount_diff": amount_diff,
                }
            )

        return results

    def get_candidate_detail(self, check_id: int) -> dict[str, Any] | None:
        """
        重複候補の詳細を取得.

        Args:
            check_id: チェックID

        Returns:
            詳細情報 (存在しない場合はNone)

        """
        check = (
            self.db.query(DuplicateCheck).filter(DuplicateCheck.id == check_id).first()
        )
        if not check:
            return None

        trans1 = check.transaction_1
        trans2 = check.transaction_2

        return {
            "check_id": check.id,
            "transaction_1": {
                "id": trans1.id,
                "date": trans1.date.strftime("%Y-%m-%d"),
                "amount": float(trans1.amount),
                "description": trans1.description or "",
                "category_major": trans1.category_major or "",
                "category_minor": trans1.category_minor or "",
                "source_file": trans1.source_file,
                "row_number": trans1.row_number,
            },
            "transaction_2": {
                "id": trans2.id,
                "date": trans2.date.strftime("%Y-%m-%d"),
                "amount": float(trans2.amount),
                "description": trans2.description or "",
                "category_major": trans2.category_major or "",
                "category_minor": trans2.category_minor or "",
                "source_file": trans2.source_file,
                "row_number": trans2.row_number,
            },
            "similarity_score": float(check.similarity_score),
            "detection_params": {
                "date_tolerance_days": check.detection_date_tolerance or 0,
                "amount_tolerance_abs": float(
                    check.detection_amount_tolerance_abs or 0
                ),
                "amount_tolerance_pct": float(
                    check.detection_amount_tolerance_pct or 0
                ),
            },
            "user_decision": check.user_decision,
            "decided_at": (
                check.decided_at.strftime("%Y-%m-%d %H:%M:%S")
                if check.decided_at
                else None
            ),
        }

    def confirm_duplicate(self, check_id: int, decision: str) -> dict[str, Any]:
        """
        重複判定を記録.

        Args:
            check_id: チェックID
            decision: 判定 ('duplicate', 'not_duplicate', 'skip')

        Returns:
            結果情報

        """
        if decision not in ["duplicate", "not_duplicate", "skip"]:
            return {
                "success": False,
                "message": f"無効な判定: {decision}",
            }

        check = (
            self.db.query(DuplicateCheck).filter(DuplicateCheck.id == check_id).first()
        )
        if not check:
            return {
                "success": False,
                "message": f"チェックID {check_id} が見つかりません",
            }

        # 判定を記録
        check.user_decision = decision
        check.decided_at = datetime.now()

        marked_transaction_id = None

        # 重複の場合、後の取引にフラグを設定
        if decision == "duplicate":
            trans1 = check.transaction_1
            trans2 = check.transaction_2

            # 日付が後のものを重複としてマーク（同じ日付なら大きいIDを重複とする）
            if trans2.date > trans1.date or (
                trans2.date == trans1.date and trans2.id > trans1.id
            ):
                duplicate_trans = trans2
                original_trans = trans1
            else:
                duplicate_trans = trans1
                original_trans = trans2

            duplicate_trans.is_duplicate = 1
            duplicate_trans.duplicate_of = original_trans.id
            duplicate_trans.duplicate_checked = 1
            duplicate_trans.duplicate_checked_at = datetime.now()

            marked_transaction_id = duplicate_trans.id

        # not_duplicateの場合、チェック済みフラグを設定
        elif decision == "not_duplicate":
            check.transaction_1.duplicate_checked = 1
            check.transaction_1.duplicate_checked_at = datetime.now()
            check.transaction_2.duplicate_checked = 1
            check.transaction_2.duplicate_checked_at = datetime.now()

        self.db.commit()

        messages = {
            "duplicate": f"重複として記録しました。取引ID {marked_transaction_id} にフラグが設定されました。",
            "not_duplicate": "重複ではないと記録しました。",
            "skip": "保留として記録しました。",
        }

        return {
            "success": True,
            "message": messages[decision],
            "marked_transaction_id": marked_transaction_id,
        }

    def restore_duplicate(self, transaction_id: int) -> dict[str, Any]:
        """
        誤って重複とマークした取引を復元.

        Args:
            transaction_id: 取引ID

        Returns:
            結果情報

        """
        trans = (
            self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        )
        if not trans:
            return {
                "success": False,
                "message": f"取引ID {transaction_id} が見つかりません",
            }

        if trans.is_duplicate == 0:
            return {
                "success": False,
                "message": f"取引ID {transaction_id} は重複としてマークされていません",
            }

        # 復元
        trans.is_duplicate = 0
        trans.duplicate_of = None
        trans.duplicate_checked = 0
        trans.duplicate_checked_at = None

        # 関連するDuplicateCheckを未判定に戻す
        checks = (
            self.db.query(DuplicateCheck)
            .filter(
                (DuplicateCheck.transaction_id_1 == transaction_id)
                | (DuplicateCheck.transaction_id_2 == transaction_id)
            )
            .filter(DuplicateCheck.user_decision == "duplicate")
            .all()
        )

        for check in checks:
            check.user_decision = None
            check.decided_at = None

        self.db.commit()

        return {
            "success": True,
            "message": f"取引ID {transaction_id} を復元しました。",
        }

    def get_stats(self) -> dict[str, Any]:
        """
        重複検出の統計情報を取得.

        Returns:
            統計情報

        """
        total_transactions = self.db.query(Transaction).count()
        duplicate_transactions = (
            self.db.query(Transaction).filter(Transaction.is_duplicate == 1).count()
        )

        total_checks = self.db.query(DuplicateCheck).count()
        pending_checks = (
            self.db.query(DuplicateCheck)
            .filter(DuplicateCheck.user_decision.is_(None))
            .count()
        )
        confirmed_duplicate = (
            self.db.query(DuplicateCheck)
            .filter(DuplicateCheck.user_decision == "duplicate")
            .count()
        )
        confirmed_not_duplicate = (
            self.db.query(DuplicateCheck)
            .filter(DuplicateCheck.user_decision == "not_duplicate")
            .count()
        )
        skipped = (
            self.db.query(DuplicateCheck)
            .filter(DuplicateCheck.user_decision == "skip")
            .count()
        )

        return {
            "total_transactions": total_transactions,
            "duplicate_transactions": duplicate_transactions,
            "total_checks": total_checks,
            "pending_checks": pending_checks,
            "confirmed_duplicate": confirmed_duplicate,
            "confirmed_not_duplicate": confirmed_not_duplicate,
            "skipped": skipped,
        }
