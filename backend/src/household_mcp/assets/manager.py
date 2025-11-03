"""Asset management service."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from household_mcp.database.models import AssetClass, AssetRecord

from .models import AssetRecordRequest, AssetRecordResponse


class AssetManager:
    """資産データの管理."""

    def __init__(self, session: Session):
        """
        初期化.

        Args:
            session: SQLAlchemyセッション

        """
        self.session = session

    def create_record(self, request: AssetRecordRequest) -> AssetRecordResponse:
        """
        資産レコード作成.

        Args:
            request: リクエストモデル

        Returns:
            作成されたレコード

        """
        record = AssetRecord(
            record_date=request.record_date,
            asset_class_id=request.asset_class_id,
            sub_asset_name=request.sub_asset_name,
            amount=request.amount,
            memo=request.memo,
        )
        self.session.add(record)
        self.session.flush()

        # リレーションを取得するため再度クエリ
        return self._record_to_response(record)

    def get_records(
        self,
        asset_class_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        include_deleted: bool = False,
    ) -> list[AssetRecordResponse]:
        """
        資産レコード一覧取得.

        Args:
            asset_class_id: 資産クラスIDフィルタ
            start_date: 開始日付
            end_date: 終了日付
            include_deleted: 削除済みを含める

        Returns:
            レコードリスト

        """
        query = self.session.query(AssetRecord)

        if not include_deleted:
            query = query.filter(AssetRecord.is_deleted == 0)

        if asset_class_id is not None:
            query = query.filter(AssetRecord.asset_class_id == asset_class_id)

        if start_date is not None:
            query = query.filter(AssetRecord.record_date >= start_date)

        if end_date is not None:
            query = query.filter(AssetRecord.record_date <= end_date)

        records = query.order_by(AssetRecord.record_date.desc()).all()
        return [self._record_to_response(r) for r in records]

    def get_record(self, record_id: int) -> Optional[AssetRecordResponse]:
        """
        資産レコード取得.

        Args:
            record_id: レコードID

        Returns:
            レコード、見つからない場合はNone

        """
        record = (
            self.session.query(AssetRecord)
            .filter(AssetRecord.id == record_id, AssetRecord.is_deleted == 0)
            .first()
        )
        if record is None:
            return None
        return self._record_to_response(record)

    def update_record(
        self, record_id: int, request: AssetRecordRequest
    ) -> AssetRecordResponse:
        """
        資産レコード更新.

        Args:
            record_id: レコードID
            request: リクエストモデル

        Returns:
            更新されたレコード

        """
        record = (
            self.session.query(AssetRecord).filter(AssetRecord.id == record_id).first()
        )
        if record is None:
            raise ValueError(f"Record {record_id} not found")

        record.record_date = request.record_date
        record.asset_class_id = request.asset_class_id
        record.sub_asset_name = request.sub_asset_name
        record.amount = request.amount
        record.memo = request.memo
        record.updated_at = datetime.now()

        self.session.flush()
        return self._record_to_response(record)

    def delete_record(self, record_id: int) -> bool:
        """
        資産レコード削除（論理削除）.

        Args:
            record_id: レコードID

        Returns:
            削除成功の有無

        """
        record = (
            self.session.query(AssetRecord).filter(AssetRecord.id == record_id).first()
        )
        if record is None:
            return False

        record.is_deleted = 1
        record.updated_at = datetime.now()
        self.session.flush()
        return True

    def get_asset_classes(self) -> list[dict]:
        """
        資産クラス一覧取得.

        Returns:
            資産クラスリスト

        """
        classes = self.session.query(AssetClass).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "display_name": c.display_name,
                "description": c.description,
                "icon": c.icon,
            }
            for c in classes
        ]

    @staticmethod
    def _record_to_response(record: AssetRecord) -> AssetRecordResponse:
        """
        レコードをレスポンスモデルに変換.

        Args:
            record: DBレコード

        Returns:
            レスポンスモデル

        """
        return AssetRecordResponse(
            id=record.id,
            record_date=record.record_date,
            asset_class_id=record.asset_class_id,
            asset_class_name=record.asset_class.display_name,
            sub_asset_name=record.sub_asset_name,
            amount=record.amount,
            memo=record.memo,
            is_manual=record.is_manual,
            source_type=record.source_type,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
