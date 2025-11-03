"""Asset management module."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssetClassResponse(BaseModel):
    """資産クラスレスポンスモデル."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    display_name: str
    description: str | None = None
    icon: str | None = None
    created_at: datetime


class AssetRecordRequest(BaseModel):
    """資産レコード作成/編集リクエストモデル."""

    record_date: datetime
    asset_class_id: int
    sub_asset_name: str
    amount: int  # JPY
    memo: str | None = None


class AssetRecordResponse(BaseModel):
    """資産レコードレスポンスモデル."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    record_date: datetime
    asset_class_id: int
    asset_class_name: str
    sub_asset_name: str
    amount: int  # JPY
    memo: str | None = None
    is_manual: int
    source_type: str
    created_at: datetime
    updated_at: datetime


class AssetSummaryResponse(BaseModel):
    """資産集計レスポンスモデル."""

    year: int
    month: int
    summary: dict  # { class_id: amount, ... }
    total: int


class AssetAllocationItem(BaseModel):
    """資産配分アイテム."""

    asset_class_id: int
    asset_class_name: str
    amount: int
    percentage: float


class AssetAllocationResponse(BaseModel):
    """資産配分レスポンスモデル."""

    allocation: list[AssetAllocationItem]
    total_assets: int
