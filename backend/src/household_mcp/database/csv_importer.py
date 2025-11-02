"""CSV to Database Importer for household MCP server."""

import glob
import os
from decimal import Decimal
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from .models import Transaction


class CSVImporter:
    """CSV → DB インポーター."""

    def __init__(self, db_session: Session):
        """初期化.

        Args:
            db_session: SQLAlchemy セッション
        """
        self.db = db_session

    def import_csv(self, csv_path: str, encoding: str = "cp932") -> Dict[str, Any]:
        """CSVファイルをDBにインポート.

        Args:
            csv_path: CSVファイルパス
            encoding: エンコーディング (デフォルト: cp932)

        Returns:
            {
                "imported": インポート件数,
                "skipped": スキップ件数,
                "errors": エラー情報リスト
            }
        """
        try:
            df = pd.read_csv(csv_path, encoding=encoding)
        except Exception as e:
            return {
                "imported": 0,
                "skipped": 0,
                "errors": [{"row": -1, "error": f"CSV読み込みエラー: {str(e)}"}],
            }

        imported = 0
        skipped = 0
        errors: List[Dict[str, Any]] = []

        source_file = os.path.basename(csv_path)

        # 1回のクエリで当該ファイルの既存 row_number を取得（重複チェックを高速化）
        existing_rows = {
            rn
            for (rn,) in self.db.query(Transaction.row_number)
            .filter(Transaction.source_file == source_file)
            .all()
        }

        to_insert: List[Transaction] = []

        for idx, row in df.iterrows():
            try:
                # インデックスを整数に変換
                row_num = int(idx) if isinstance(idx, (int, float)) else 0

                # 既存ならスキップ（ユニーク制約 idx_source_file_row にも一致）
                if row_num in existing_rows:
                    skipped += 1
                    continue

                # 日付解析
                date_value = pd.to_datetime(row["日付"])

                # 金額をDecimalに変換（全角・半角括弧両対応）
                amount_key = "金額（円）" if "金額（円）" in row else "金額(円)"
                amount_value = Decimal(str(row[amount_key]))

                # 新規登録オブジェクト作成（後で一括挿入）
                trans = Transaction(
                    source_file=source_file,
                    row_number=row_num,
                    date=date_value,
                    amount=amount_value,
                    description=row.get("内容", ""),
                    category_major=row.get("大項目", row.get("大分類", "")),
                    category_minor=row.get("中項目", row.get("中分類", "")),
                    account=row.get("口座", ""),
                    memo=row.get("メモ", ""),
                    is_target=int(row.get("計算対象", 1)),
                )

                to_insert.append(trans)
                imported += 1

            except Exception as e:
                row_num = int(idx) if isinstance(idx, (int, float)) else -1
                errors.append({"row": row_num, "error": str(e)})

        # 一括挿入で高速化
        try:
            if to_insert:
                # bulk_save_objects は ORM オブジェクトの一括挿入で高速
                self.db.bulk_save_objects(to_insert, return_defaults=False)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            errors.append({"row": -1, "error": f"コミットエラー: {str(e)}"})
            # コミット失敗時はインポート数を0扱いに戻す
            imported = 0

        return {"imported": imported, "skipped": skipped, "errors": errors}

    def import_all_csvs(self, data_dir: str = "data") -> Dict[str, Any]:
        """dataディレクトリ内の全CSVをインポート.

        Args:
            data_dir: データディレクトリパス (デフォルト: "data")

        Returns:
            {
                "files_processed": 処理ファイル数,
                "total_imported": 合計インポート件数,
                "total_skipped": 合計スキップ件数,
                "errors": 全エラー情報リスト
            }
        """
        csv_pattern = os.path.join(data_dir, "収入・支出詳細_*.csv")
        csv_files = glob.glob(csv_pattern)

        if not csv_files:
            return {
                "files_processed": 0,
                "total_imported": 0,
                "total_skipped": 0,
                "errors": [{"file": data_dir, "error": "CSVファイルが見つかりません"}],
            }

        total_imported = 0
        total_skipped = 0
        all_errors: List[Dict[str, Any]] = []

        for csv_file in sorted(csv_files):
            result = self.import_csv(csv_file)
            total_imported += result["imported"]
            total_skipped += result["skipped"]

            # ファイル名をエラー情報に追加
            for error in result["errors"]:
                error["file"] = os.path.basename(csv_file)
                all_errors.append(error)

        return {
            "files_processed": len(csv_files),
            "total_imported": total_imported,
            "total_skipped": total_skipped,
            "errors": all_errors,
        }
