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

        # 全ペア比較の前に、日付と金額で候補をバケット化して比較数を削減
        grouped = self._group_transactions(transactions)

        for date_key, bucket_map in grouped.items():
            # amount バケットがない場合（割合許容のみなど）は従来ロジック
            if bucket_map is None:
                date_group = self._legacy_date_group(transactions, date_key)
                for i, trans1 in enumerate(date_group):
                    for trans2 in date_group[i + 1 :]:
                        if self._is_potential_duplicate(trans1, trans2):
                            score = self._calculate_similarity(trans1, trans2)
                            if score >= self.options.min_similarity_score:
                                candidates.append((trans1, trans2, score))
                continue

            # 絶対誤差ベースなどでバケットがある場合は、同一・隣接バケットのみ比較
            sorted_keys = sorted(bucket_map.keys())
            for idx, bkey in enumerate(sorted_keys):
                current = bucket_map[bkey]
                # 隣接（+1）バケットとだけ比較すれば重複なく網羅できる
                neighbors = (
                    bucket_map.get(sorted_keys[idx + 1], [])
                    if idx + 1 < len(sorted_keys)
                    else []
                )

                # 同一バケット内比較
                for i, t1 in enumerate(current):
                    for t2 in current[i + 1 :]:
                        if self._is_potential_duplicate(t1, t2):
                            score = self._calculate_similarity(t1, t2)
                            if score >= self.options.min_similarity_score:
                                candidates.append((t1, t2, score))

                # 隣接バケットとの比較
                if neighbors:
                    for t1 in current:
                        for t2 in neighbors:
                            if self._is_potential_duplicate(t1, t2):
                                score = self._calculate_similarity(t1, t2)
                                if score >= self.options.min_similarity_score:
                                    candidates.append((t1, t2, score))

        # スコア降順でソート
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates

    def _group_transactions(
        self, transactions: List[Transaction]
    ) -> Dict[Tuple[int, int, int], Optional[Dict[int, List[Transaction]]]]:
        """日付と金額のバケットでトランザクションをグルーピング.

        - 日付トレランスが0なら日単位、そうでなければ月単位。
        - 金額許容が0なら金額の完全一致でまとめる。
        - 絶対誤差許容がある場合は、その幅で金額バケット化（隣接バケットも比較）。
        - 割合誤差のみのときは金額バケットは使わず（None を返し）従来方式にフォールバック。

        Returns:
            {(y, m, d_or_0): {amount_bucket: [transactions]} | None}
        """
        use_day = self.options.date_tolerance_days == 0
        abs_tol = self.options.amount_tolerance_abs
        pct_tol = self.options.amount_tolerance_pct

        grouped: Dict[Tuple[int, int, int], Optional[Dict[int, List[Transaction]]]] = {}

        def date_key_of(t: Transaction) -> Tuple[int, int, int]:
            if use_day:
                return (t.date.year, t.date.month, t.date.day)
            return (t.date.year, t.date.month, 0)

        def amount_bucket_of(t: Transaction) -> Optional[int]:
            amount = abs(float(t.amount))
            if abs_tol == 0 and pct_tol == 0:
                # 0.01円単位で正規化して固定バケットへ（完全一致用）
                return int(round(amount * 100))
            if abs_tol > 0:
                return int(amount // abs_tol)
            # 割合許容のみ → バケット化せず従来方式
            return None

        # 第1段階: 日付キーで分割
        by_date: Dict[Tuple[int, int, int], List[Transaction]] = {}
        for t in transactions:
            dk = date_key_of(t)
            by_date.setdefault(dk, []).append(t)

        # 第2段階: 金額バケット化（可能なら）
        for dk, items in by_date.items():
            sample_bucket = amount_bucket_of(items[0]) if items else None
            if sample_bucket is None and abs_tol == 0 and pct_tol > 0:
                # 割合許容のみ → None を設定して従来方式を使う
                grouped[dk] = None
                continue

            if sample_bucket is None and abs_tol == 0 and pct_tol == 0:
                # 完全一致モードでも None になることはないが安全のため
                grouped[dk] = None
                continue

            buckets: Dict[int, List[Transaction]] = {}
            for t in items:
                b = amount_bucket_of(t)
                if b is None:
                    # 念のためのフォールバック
                    grouped[dk] = None
                    buckets = {}
                    break
                buckets.setdefault(b, []).append(t)
            if buckets:
                grouped[dk] = buckets

        return grouped

    def _legacy_date_group(
        self, all_transactions: List[Transaction], date_key: Tuple[int, int, int]
    ) -> List[Transaction]:
        """従来の月単位グルーピングの簡易版（フォールバック用）."""
        y, m, d = date_key
        if d == 0:
            return [
                t for t in all_transactions if t.date.year == y and t.date.month == m
            ]
        return [
            t
            for t in all_transactions
            if t.date.year == y and t.date.month == m and t.date.day == d
        ]

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
