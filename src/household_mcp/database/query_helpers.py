"""Query helpers for aggregating transactions with duplicate exclusion."""

# mypy: disable-error-code="no-any-return,arg-type,misc"

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from household_mcp.database.models import Transaction


def get_active_transactions(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    category: Optional[str] = None,
    exclude_duplicates: bool = True,
) -> List[Transaction]:
    """集計対象の取引を取得（重複除外オプション付き）.

    Args:
        db: データベースセッション
        start_date: 開始日（Noneの場合は制限なし）
        end_date: 終了日（Noneの場合は制限なし）
        category: カテゴリフィルタ（Noneの場合は全カテゴリ）
        exclude_duplicates: 重複を除外するか（デフォルト: True）

    Returns:
        取引のリスト
    """
    query = db.query(Transaction)

    if exclude_duplicates:
        query = query.filter(Transaction.is_duplicate == 0)

    if start_date:
        query = query.filter(Transaction.date >= start_date)

    if end_date:
        query = query.filter(Transaction.date <= end_date)

    if category:
        query = query.filter(Transaction.category_major == category)

    return query.order_by(Transaction.date, Transaction.id).all()


def get_monthly_summary(
    db: Session, year: int, month: int, exclude_duplicates: bool = True
) -> Dict[str, Any]:
    """月次サマリーを取得.

    Args:
        db: データベースセッション
        year: 年
        month: 月
        exclude_duplicates: 重複を除外するか（デフォルト: True）

    Returns:
        {
            "total_income": 100000.0,
            "total_expense": -80000.0,
            "net": 20000.0,
            "transaction_count": 50,
            "duplicate_count": 2
        }
    """
    # 月の開始日と終了日を計算
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    # 基本クエリ
    base_query = db.query(Transaction).filter(
        Transaction.date >= start_date, Transaction.date < end_date
    )

    # 重複除外クエリ
    if exclude_duplicates:
        active_query = base_query.filter(Transaction.is_duplicate == 0)
    else:
        active_query = base_query

    # 集計
    transactions = active_query.all()

    total_income = sum(float(t.amount) for t in transactions if float(t.amount) > 0)
    total_expense = sum(float(t.amount) for t in transactions if float(t.amount) < 0)

    # 重複カウント（参考情報）
    duplicate_count = base_query.filter(Transaction.is_duplicate == 1).count()

    return {
        "total_income": total_income,
        "total_expense": total_expense,
        "net": total_income + total_expense,
        "transaction_count": len(transactions),
        "duplicate_count": duplicate_count,
    }


def get_category_breakdown(
    db: Session,
    start_date: date,
    end_date: date,
    exclude_duplicates: bool = True,
) -> List[Dict[str, Any]]:
    """カテゴリ別集計を取得.

    Args:
        db: データベースセッション
        start_date: 開始日
        end_date: 終了日
        exclude_duplicates: 重複を除外するか（デフォルト: True）

    Returns:
        [
            {
                "category": "食費",
                "total_amount": -50000.0,
                "transaction_count": 30
            },
            ...
        ]
    """
    query = db.query(
        Transaction.category_major,
        func.sum(Transaction.amount).label("total_amount"),
        func.count(Transaction.id).label("transaction_count"),
    ).filter(Transaction.date >= start_date, Transaction.date <= end_date)

    if exclude_duplicates:
        query = query.filter(Transaction.is_duplicate == 0)

    query = query.group_by(Transaction.category_major).order_by(
        func.sum(Transaction.amount)
    )

    results = query.all()

    return [
        {
            "category": row.category_major,
            "total_amount": float(row.total_amount or 0),
            "transaction_count": row.transaction_count,
        }
        for row in results
    ]


def get_duplicate_impact_report(db: Session, year: int, month: int) -> Dict[str, Any]:
    """重複が集計に与える影響のレポートを生成.

    Args:
        db: データベースセッション
        year: 年
        month: 月

    Returns:
        {
            "with_duplicates": {...},
            "without_duplicates": {...},
            "impact": {
                "expense_difference": -5000.0,
                "duplicate_transaction_count": 2
            }
        }
    """
    with_dup = get_monthly_summary(db, year, month, exclude_duplicates=False)
    without_dup = get_monthly_summary(db, year, month, exclude_duplicates=True)

    return {
        "with_duplicates": with_dup,
        "without_duplicates": without_dup,
        "impact": {
            "expense_difference": with_dup["total_expense"]
            - without_dup["total_expense"],
            "income_difference": with_dup["total_income"] - without_dup["total_income"],
            "duplicate_transaction_count": with_dup["duplicate_count"],
        },
    }
