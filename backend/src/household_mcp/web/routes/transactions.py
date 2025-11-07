"""Transaction CRUD API routes for Phase 13."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from household_mcp.database import DatabaseManager, Transaction

router = APIRouter(prefix="/api/transactions", tags=["transactions"])
db_manager = DatabaseManager(db_path="data/household.db")

# API-generated transactions use a unique identifier
_api_transaction_counter = 10000


def _get_api_row_number() -> int:
    """Generate unique row_number for API-created transactions."""
    global _api_transaction_counter
    # Use negative numbers to avoid conflict with CSV imports
    _api_transaction_counter -= 1
    return _api_transaction_counter


class TransactionCreateRequest(BaseModel):
    """取引作成リクエストスキーマ."""

    date: datetime = Field(..., description="取引日付")
    amount: float = Field(..., description="金額（円）")
    description: str = Field(default="", description="説明")
    category_major: str = Field(default="", description="大カテゴリ")
    category_minor: str = Field(default="", description="中カテゴリ")
    account: str = Field(default="", description="口座")
    memo: str = Field(default="", description="メモ")
    is_target: int = Field(default=1, description="計算対象フラグ")


class TransactionResponse(BaseModel):
    """取引レスポンススキーマ."""

    id: int
    date: datetime
    amount: float
    description: str
    category_major: str
    category_minor: str
    account: str
    memo: str | None = None
    is_target: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


@router.post("/create", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    req: TransactionCreateRequest,
) -> TransactionResponse:
    """
    取引を作成.

    Args:
        req: 取引作成リクエスト

    Returns:
        作成された取引オブジェクト

    Raises:
        HTTPException: バリデーションエラー時

    """
    try:
        with db_manager.session_scope() as session:
            transaction = Transaction(
                source_file="api",
                row_number=_get_api_row_number(),  # Unique negative number
                date=req.date,
                amount=req.amount,
                description=req.description,
                category_major=req.category_major,
                category_minor=req.category_minor,
                account=req.account,
                memo=req.memo,
                is_target=req.is_target,
            )
            session.add(transaction)
            session.flush()  # IDを取得するためにflush
            return TransactionResponse.model_validate(transaction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"バリデーションエラー: {e}") from e


@router.get("/list", response_model=list[TransactionResponse])
async def list_transactions(
    start_date: datetime | None = Query(  # noqa: B008
        None, description="開始日"
    ),
    end_date: datetime | None = Query(  # noqa: B008
        None, description="終了日"
    ),
    category_major: str | None = Query(None, description="大カテゴリフィルタ"),
    limit: int = Query(100, ge=1, le=1000, description="件数上限"),
    offset: int = Query(0, ge=0, description="オフセット"),
) -> list[TransactionResponse]:
    """
    取引一覧を取得（フィルタ対応）.

    Args:
        start_date: 開始日フィルタ
        end_date: 終了日フィルタ
        category_major: 大カテゴリフィルタ
        limit: 最大件数
        offset: オフセット

    Returns:
        フィルタ済み取引リスト

    """
    with db_manager.session_scope() as session:
        query = session.query(Transaction)

        if start_date:
            query = query.filter(Transaction.date >= start_date)
        if end_date:
            query = query.filter(Transaction.date <= end_date)
        if category_major:
            query = query.filter(Transaction.category_major == category_major)

        query = query.order_by(Transaction.date.desc())
        query = query.limit(limit).offset(offset)
        transactions = query.all()
        return [TransactionResponse.model_validate(tx) for tx in transactions]


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: int) -> TransactionResponse:
    """
    取引を ID で取得.

    Args:
        transaction_id: 取引 ID

    Returns:
        取引オブジェクト

    Raises:
        HTTPException: 取引が見つからない場合

    """
    with db_manager.session_scope() as session:
        transaction = (
            session.query(Transaction).filter(Transaction.id == transaction_id).first()
        )

        if not transaction:
            raise HTTPException(status_code=404, detail="取引が見つかりません")

        return TransactionResponse.model_validate(transaction)


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: int, req: TransactionCreateRequest
) -> TransactionResponse:
    """
    取引を更新.

    Args:
        transaction_id: 取引 ID
        req: 更新リクエスト

    Returns:
        更新された取引オブジェクト

    Raises:
        HTTPException: 取引が見つからない場合

    """
    with db_manager.session_scope() as session:
        transaction = (
            session.query(Transaction).filter(Transaction.id == transaction_id).first()
        )

        if not transaction:
            raise HTTPException(status_code=404, detail="取引が見つかりません")

        transaction.date = req.date
        transaction.amount = req.amount
        transaction.description = req.description
        transaction.category_major = req.category_major
        transaction.category_minor = req.category_minor
        transaction.account = req.account
        transaction.memo = req.memo
        transaction.is_target = req.is_target

        session.merge(transaction)
        return TransactionResponse.model_validate(transaction)


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(transaction_id: int) -> None:
    """
    取引を削除.

    Args:
        transaction_id: 取引 ID

    Raises:
        HTTPException: 取引が見つからない場合

    """
    with db_manager.session_scope() as session:
        transaction = (
            session.query(Transaction).filter(Transaction.id == transaction_id).first()
        )

        if not transaction:
            raise HTTPException(status_code=404, detail="取引が見つかりません")

        session.delete(transaction)
