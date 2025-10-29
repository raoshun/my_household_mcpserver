"""Duplicate detection engine for household MCP server."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from household_mcp.database.models import Transaction


@dataclass
class DetectionOptions:
    """重複検出オプション."""

    date_tolerance_days: int = 0  # 日付誤差許容(±日数)
    amount_tolerance_abs: float = 0.0  # 金額絶対誤差(±円)
    amount_tolerance_pct: float = 0.0  # 金額割合誤差(±%)
    min_similarity_score: float = 0.8  # 最小類似度スコア


class DuplicateDetector:
    """重複検出エンジン."""

    def __init__(self, db_session: Session, options: Optional[DetectionOptions] = None):
        """初期化.

        Args:
            db_session: SQLAlchemy セッション
            options: 検出オプション
        """
        self.db = db_session
        self.options = options or DetectionOptions()

    def detect_duplicates(
        self, transaction_ids: Optional[List[int]] = None
    ) -> List[Tuple[Transaction, Transaction, float]]:
        """重複候補を検出.

        Args:
            transaction_ids: 検出対象の取引IDリスト。Noneの場合は全件検索

        Returns:
            (取引1, 取引2, 類似度スコア) のリスト（スコア降順）
        """
        candidates: List[Tuple[Transaction, Transaction, float]] = []

        # 検出対象の取得（is_duplicate=0 のみ）
        query = self.db.query(Transaction).filter(Transaction.is_duplicate == 0)
        if transaction_ids:
            query = query.filter(Transaction.id.in_(transaction_ids))

        transactions = query.all()

        # 全ペアの比較（効率化のため日付でグルーピング）
        grouped = self._group_by_date_range(transactions)

        for date_group in grouped.values():
            for i, trans1 in enumerate(date_group):
                for trans2 in date_group[i + 1 :]:
                    if self._is_potential_duplicate(trans1, trans2):
                        score = self._calculate_similarity(trans1, trans2)
                        if score >= self.options.min_similarity_score:
                            candidates.append((trans1, trans2, score))

        # スコア降順でソート
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates

    def _group_by_date_range(
        self, transactions: List[Transaction]
    ) -> Dict[Tuple[int, int], List[Transaction]]:
        """日付範囲でグルーピング（効率化）.

        Args:
            transactions: 取引リスト

        Returns:
            {(year, month): [transactions]} の辞書
        """
        groups: Dict[Tuple[int, int], List[Transaction]] = {}

        for trans in transactions:
            # 月単位でグルーピング（日付許容範囲内での比較を可能にする）
            key = (trans.date.year, trans.date.month)
            if key not in groups:
                groups[key] = []
            groups[key].append(trans)

        return groups

    def _is_potential_duplicate(self, trans1: Transaction, trans2: Transaction) -> bool:
        """基本条件チェック（高速フィルタリング）.

        Args:
            trans1: 取引1
            trans2: 取引2

        Returns:
            重複候補かどうか
        """
        # 日付チェック
        date_diff = abs((trans1.date - trans2.date).days)
        if date_diff > self.options.date_tolerance_days:
            return False

        # 金額チェック
        amount1_float = float(trans1.amount)
        amount2_float = float(trans2.amount)

        # 誤差許容が設定されていない場合は完全一致のみ
        if (
            self.options.amount_tolerance_abs == 0
            and self.options.amount_tolerance_pct == 0
        ):
            if amount1_float != amount2_float:
                return False
        else:
            # 絶対値誤差チェック
            if self.options.amount_tolerance_abs > 0:
                amount_diff_abs = abs(amount1_float - amount2_float)
                if amount_diff_abs > self.options.amount_tolerance_abs:
                    return False

            # 割合誤差チェック
            if self.options.amount_tolerance_pct > 0:
                avg_amount = (abs(amount1_float) + abs(amount2_float)) / 2
                if avg_amount > 0:
                    amount_diff_pct = (
                        abs(amount1_float - amount2_float) / avg_amount * 100
                    )
                    if amount_diff_pct > self.options.amount_tolerance_pct:
                        return False

        return True

    def _calculate_similarity(self, trans1: Transaction, trans2: Transaction) -> float:
        """類似度スコア計算 (0.0-1.0).

        Args:
            trans1: 取引1
            trans2: 取引2

        Returns:
            類似度スコア（0.0-1.0）
        """
        score = 0.0

        # 日付の類似度（重み 0.4）
        date_diff = abs((trans1.date - trans2.date).days)
        if self.options.date_tolerance_days > 0:
            # 許容範囲内での相対的な近さを計算
            date_sim = 1.0 - (date_diff / (self.options.date_tolerance_days + 1))
        else:
            # 許容なしの場合は完全一致のみ1.0
            date_sim = 1.0 if date_diff == 0 else 0.0
        score += date_sim * 0.4

        # 金額の類似度（重み 0.6）
        amount1 = abs(float(trans1.amount))
        amount2 = abs(float(trans2.amount))
        max_amount = max(amount1, amount2)
        if max_amount > 0:
            amount_sim = 1.0 - abs(amount1 - amount2) / max_amount
        else:
            amount_sim = 1.0
        score += amount_sim * 0.6

        return float(score)
