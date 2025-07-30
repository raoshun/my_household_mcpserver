"""家計簿データ管理ツール.

取引、カテゴリー、アカウントのCRUD操作を提供
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from ..database.connection import DatabaseConnection, get_database_connection
from ..database.models import Transaction

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """データ検証エラー."""

    def __init__(self, message: str):
        """初期化.

        Args:
            message: エラーメッセージ
        """
        self.message = message
        super().__init__(self.message)


class TransactionManager:
    """取引データ管理クラス."""

    def __init__(self):
        """初期化."""
        self.db_connection = get_database_connection()

    def add_transaction(
        self,
        date: str,
        amount: float,
        description: str,
        category_name: str,
        account_name: str,
        type: str,
    ) -> Dict[str, Any]:
        """新しい取引を追加.

        Args:
            date: 取引日 (YYYY-MM-DD形式)
            amount: 金額
            description: 説明
            category_name: カテゴリー名
            account_name: アカウント名
            type: 取引タイプ ('income' or 'expense')

        Returns:
            追加された取引の情報

        Raises:
            DataValidationError: データ検証エラー
        """
        try:
            # データ検証
            self._validate_transaction_data(
                date, amount, description, category_name, account_name, type
            )

            # カテゴリーIDとアカウントIDを取得
            category_id = self._get_category_id(category_name, type)
            account_id = self._get_account_id(account_name)

            # 取引データを作成
            transaction = Transaction(
                date=datetime.strptime(date, "%Y-%m-%d").date(),
                amount=Decimal(str(amount)),
                description=description,
                category_id=category_id,
                account_id=account_id,
                type=type,
            )

            # データベースに挿入
            with self.db_connection.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO transactions (date, amount, description, category_id,
                    account_id, type) VALUES (?, ?, ?, ?, ?, ?)"""
                                                                  ,
                    (
                        transaction.date,
                        transaction.amount,
                        transaction.description,
                        transaction.category_id,
                        transaction.account_id,
                        transaction.type,
                    ),
                )
                transaction_id = cursor.lastrowid
                transaction.id = transaction_id

                # アカウント残高を更新
                self._update_account_balance(conn, account_id, amount, type)

            logger.info("Transaction added successfully: ID=%s", transaction_id)

            return {
                "success": True,
                "transaction_id": transaction_id,
                "message": f"取引を追加しました（ID: {transaction_id}）",
                "data": {
                    "id": transaction_id,
                    "date": str(transaction.date),
                    "amount": float(transaction.amount) if transaction.amount else 0.0,
                    "description": transaction.description,
                    "category": category_name,
                    "account": account_name,
                    "type": transaction.type,
                },
            }

        except Exception as e:
            logger.error("Failed to add transaction: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": f"取引の追加に失敗しました: {str(e)}",
            }

    def get_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        category_name: Optional[str] = None,
        account_name: Optional[str] = None,
        transaction_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """取引一覧を取得.

        Args:
            limit: 取得件数の上限
            offset: オフセット
            start_date: 開始日
            end_date: 終了日
            category_name: カテゴリー名でフィルタ
            account_name: アカウント名でフィルタ
            transaction_type: 取引タイプでフィルタ

        Returns:
            取引一覧
        """
        try:
            # クエリ条件を構築
            conditions = []
            params = []

            if start_date:
                conditions.append("t.date >= ?")
                params.append(start_date)

            if end_date:
                conditions.append("t.date <= ?")
                params.append(end_date)

            if category_name:
                conditions.append("c.name = ?")
                params.append(category_name)

            if account_name:
                conditions.append("a.name = ?")
                params.append(account_name)

            if transaction_type:
                conditions.append("t.type = ?")
                params.append(transaction_type)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            query = f"""
                SELECT
                    t.id, t.date, t.amount, t.description, t.type,
                    c.name as category_name, a.name as account_name,
                    t.created_at, t.updated_at
                FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN accounts a ON t.account_id = a.id
                {where_clause}
                ORDER BY t.date DESC, t.id DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])

            result = self.db_connection.execute_query(
                query, tuple(params), fetch_all=True
            )

            transactions = []
            if result:
                for row in result:
                    transactions.append(
                        {
                            "id": row[0],
                            "date": row[1],
                            "amount": float(row[2]) if row[2] else 0.0,
                            "description": row[3],
                            "type": row[4],
                            "category": row[5],
                            "account": row[6],
                            "created_at": row[7],
                            "updated_at": row[8],
                        }
                    )

            # 総件数を取得
            count_query = f"""
                SELECT COUNT(*) FROM transactions t
                LEFT JOIN categories c ON t.category_id = c.id
                LEFT JOIN accounts a ON t.account_id = a.id
                {where_clause}
            """

            count_result = self.db_connection.execute_query(
                count_query, tuple(params[:-2]), fetch_one=True
            )
            total_count = count_result[0] if count_result else 0

            return {
                "success": True,
                "data": {
                    "transactions": transactions,
                    "pagination": {
                        "total_count": total_count,
                        "limit": limit,
                        "offset": offset,
                        "has_next": offset + limit < total_count,
                    },
                },
                "message": f"{len(transactions)}件の取引を取得しました",
            }

        except Exception as e:
            logger.error("Failed to get transactions: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": f"取引の取得に失敗しました: {str(e)}",
            }

    def update_transaction(self, transaction_id: int, **kwargs) -> Dict[str, Any]:
        """取引を更新.

        Args:
            transaction_id: 取引ID
            **kwargs: 更新する項目

        Returns:
            更新結果
        """
        try:
            # 既存の取引を取得
            existing = self._get_transaction_by_id(transaction_id)
            if not existing:
                return {
                    "success": False,
                    "error": "Transaction not found",
                    "message": f"ID {transaction_id} の取引が見つかりません",
                }

            # 更新可能フィールドを定義
            allowed_fields = [
                "date",
                "amount",
                "description",
                "category_name",
                "account_name",
            ]
            update_fields = []
            update_params = []

            for field, value in kwargs.items():
                if field in allowed_fields and value is not None:
                    if field == "date":
                        update_fields.append("date = ?")
                        update_params.append(
                            datetime.strptime(value, "%Y-%m-%d").date()
                        )
                    elif field == "amount":
                        update_fields.append("amount = ?")
                        update_params.append(Decimal(str(value)))
                    elif field == "description":
                        update_fields.append("description = ?")
                        update_params.append(value)
                    elif field == "category_name":
                        category_id = self._get_category_id(value, existing["type"])
                        update_fields.append("category_id = ?")
                        update_params.append(category_id)
                    elif field == "account_name":
                        account_id = self._get_account_id(value)
                        update_fields.append("account_id = ?")
                        update_params.append(account_id)

            if not update_fields:
                return {
                    "success": False,
                    "error": "No valid fields to update",
                    "message": "更新対象のフィールドがありません",
                }

            # updated_atを追加
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            update_params.append(transaction_id)

            query = f"""
                UPDATE transactions
                SET {', '.join(update_fields)}
                WHERE id = ?
            """

            with self.db_connection.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(query, tuple(update_params))

                if cursor.rowcount == 0:
                    return {
                        "success": False,
                        "error": "No rows updated",
                        "message": "取引の更新に失敗しました",
                    }

            logger.info("Transaction updated successfully: ID=%s", transaction_id)

            return {
                "success": True,
                "transaction_id": transaction_id,
                "message": f"取引を更新しました（ID: {transaction_id}）",
            }

        except Exception as e:
            logger.error("Failed to update transaction: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": f"取引の更新に失敗しました: {str(e)}",
            }

    def delete_transaction(self, transaction_id: int) -> Dict[str, Any]:
        """取引を削除.

        Args:
            transaction_id: 取引ID

        Returns:
            削除結果
        """
        try:
            # 既存の取引を取得
            existing = self._get_transaction_by_id(transaction_id)
            if not existing:
                return {
                    "success": False,
                    "error": "Transaction not found",
                    "message": f"ID {transaction_id} の取引が見つかりません",
                }

            with self.db_connection.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM transactions WHERE id = ?", (transaction_id,)
                )

                if cursor.rowcount == 0:
                    return {
                        "success": False,
                        "error": "No rows deleted",
                        "message": "取引の削除に失敗しました",
                    }

                # アカウント残高を逆算で調整
                amount = existing["amount"]
                account_id = existing["account_id"]
                transaction_type = existing["type"]

                # 削除時は逆の操作を行う
                reverse_amount = -amount if transaction_type == "expense" else amount
                reverse_type = "income" if transaction_type == "expense" else "expense"

                self._update_account_balance(
                    conn, account_id, reverse_amount, reverse_type
                )

            logger.info("Transaction deleted successfully: ID=%s", transaction_id)

            return {
                "success": True,
                "transaction_id": transaction_id,
                "message": f"取引を削除しました（ID: {transaction_id}）",
            }

        except Exception as e:
            logger.error("Failed to delete transaction: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": f"取引の削除に失敗しました: {str(e)}",
            }

    def _validate_transaction_data(
        self,
        date: str,
        amount: float,
        description: str,
        category_name: str,
        account_name: str,
        type: str,
    ) -> None:
        """取引データの検証."""
        if not date:
            raise DataValidationError("日付は必須です")

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise DataValidationError("日付はYYYY-MM-DD形式で入力してください")

        if amount is None or amount <= 0:
            raise DataValidationError("金額は正の数値である必要があります")

        if not description or not description.strip():
            raise DataValidationError("説明は必須です")

        if type not in ["income", "expense"]:
            raise DataValidationError(
                "取引タイプは 'income' または 'expense' である必要があります"
            )

        if not category_name or not category_name.strip():
            raise DataValidationError("カテゴリー名は必須です")

        if not account_name or not account_name.strip():
            raise DataValidationError("アカウント名は必須です")

    def _get_category_id(self, category_name: str, transaction_type: str) -> int:
        """カテゴリー名からIDを取得（存在しない場合は作成）."""
        query = "SELECT id FROM categories WHERE name = ? AND type = ?"
        result = self.db_connection.execute_query(
            query, (category_name, transaction_type), fetch_one=True
        )

        if result:
            return result[0]

        # カテゴリーが存在しない場合は作成
        with self.db_connection.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO categories (name, type) VALUES (?, ?)",
                (category_name, transaction_type),
            )
            last_id = cursor.lastrowid
            if last_id is None:
                raise DataValidationError("カテゴリーの作成に失敗しました")
            return last_id

    def _get_account_id(self, account_name: str) -> int:
        """アカウント名からIDを取得（存在しない場合はエラー）."""
        query = "SELECT id FROM accounts WHERE name = ?"
        result = self.db_connection.execute_query(
            query, (account_name,), fetch_one=True
        )

        if result:
            return result[0]

        raise DataValidationError(f"アカウント '{account_name}' が見つかりません")

    def _get_transaction_by_id(self, transaction_id: int) -> Optional[Dict[str, Any]]:
        """IDで取引を取得."""
        query = """
            SELECT t.*, c.name as category_name, a.name as account_name
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.id
            LEFT JOIN accounts a ON t.account_id = a.id
            WHERE t.id = ?
        """
        result = self.db_connection.execute_query(
            query, (transaction_id,), fetch_one=True
        )

        if result:
            return {
                "id": result[0],
                "date": result[1],
                "amount": result[2],
                "description": result[3],
                "category_id": result[4],
                "account_id": result[5],
                "type": result[6],
                "created_at": result[7],
                "updated_at": result[8],
                "category_name": result[9],
                "account_name": result[10],
            }

        return None

    def _update_account_balance(
        self, connection, account_id: int, amount: float, transaction_type: str
    ) -> None:
        """アカウント残高を更新."""
        # 収入の場合は残高を増やし、支出の場合は残高を減らす
        balance_change = amount if transaction_type == "income" else -amount

        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE accounts
            SET current_balance = current_balance + ?
            WHERE id = ?
            """\
               ,
            (Decimal(str(balance_change)), account_id),
        )


# グローバルなTransactionManagerインスタンス
_transaction_manager: Optional[TransactionManager] = None


def get_transaction_manager() -> TransactionManager:
    """TransactionManagerのシングルトンインスタンスを取得."""
    global _transaction_manager

    if _transaction_manager is None:
        _transaction_manager = TransactionManager()

    return _transaction_manager


class CategoryManager:
    """カテゴリー管理クラス."""

    def __init__(self):
        """初期化."""
        self.db_connection = get_database_connection()

    def get_categories(self, category_type: Optional[str] = None) -> Dict[str, Any]:
        """カテゴリー一覧を取得.

        Args:
            category_type: カテゴリータイプ ('income' または 'expense')

        Returns:
            カテゴリー一覧
        """
        try:
            query = "SELECT id, name, type, parent_id, color, icon FROM categories"
            params = []

            if category_type:
                query += " WHERE type = ?"
                params.append(category_type)

            query += " ORDER BY name"

            result = self.db_connection.execute_query(
                query, tuple(params), fetch_all=True
            )

            categories = []
            if result:
                for row in result:
                    categories.append(
                        {
                            "id": row[0],
                            "name": row[1],
                            "type": row[2],
                            "parent_id": row[3],
                            "color": row[4],
                            "icon": row[5],
                        }
                    )

            return {"success": True, "categories": categories, "count": len(categories)}

        except Exception as e:
            logger.error("Failed to get categories: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "カテゴリー一覧の取得に失敗しました",
            }

    def add_category(
        self,
        name: str,
        category_type: str,
        parent_id: Optional[int] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Dict[str, Any]:
        """新しいカテゴリーを追加.

        Args:
            name: カテゴリー名
            category_type: カテゴリータイプ ('income' または 'expense')
            parent_id: 親カテゴリーID
            color: カテゴリー色
            icon: カテゴリーアイコン

        Returns:
            追加結果
        """
        try:
            # 入力検証
            if category_type not in ["income", "expense"]:
                raise DataValidationError(
                    "カテゴリータイプは 'income' または 'expense' である必要があります"
                )

            if not name or not name.strip():
                raise DataValidationError("カテゴリー名は必須です")

            # 同名カテゴリーの存在確認
            existing = self.db_connection.execute_query(
                "SELECT id FROM categories WHERE name = ? AND type = ?",
                (name.strip(), category_type),
                fetch_one=True,
            )

            if existing:
                return {
                    "success": False,
                    "error": "DUPLICATE_CATEGORY",
                    "message": f"カテゴリー '{name}' は既に存在します",
                }

            # カテゴリー追加
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """INSERT INTO categories (name, type, parent_id, color, icon)
                    VALUES (?, ?, ?, ?, ?)"""
                                             ,
                    (name.strip(), category_type, parent_id, color, icon),
                )

                category_id = cursor.lastrowid

            return {
                "success": True,
                "message": f"カテゴリー '{name}' を追加しました",
                "category_id": category_id,
            }

        except DataValidationError as e:
            return {"success": False, "error": "VALIDATION_ERROR", "message": e.message}
        except Exception as e:
            logger.error("Failed to add category: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "カテゴリーの追加に失敗しました",
            }

    def update_category(self, category_id: int, **kwargs) -> Dict[str, Any]:
        """カテゴリーを更新.

        Args:
            category_id: カテゴリーID
            **kwargs: 更新するフィールド

        Returns:
            更新結果
        """
        try:
            # カテゴリーの存在確認
            existing = self.db_connection.execute_query(
                "SELECT id, name FROM categories WHERE id = ?",
                (category_id,),
                fetch_one=True,
            )

            if not existing:
                return {
                    "success": False,
                    "error": "NOT_FOUND",
                    "message": f"カテゴリーID {category_id} が見つかりません",
                }

            # 更新可能フィールドをフィルタリング
            allowed_fields = ["name", "type", "parent_id", "color", "icon"]
            update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}

            if not update_fields:
                return {
                    "success": False,
                    "error": "NO_UPDATE_FIELDS",
                    "message": "更新するフィールドが指定されていません",
                }

            # 型検証
            if "type" in update_fields and update_fields["type"] not in [
                "income",
                "expense",
            ]:
                raise DataValidationError(
                    "カテゴリータイプは 'income' または 'expense' である必要があります"
                )

            # 更新実行
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()

                set_clause = ", ".join(
                    [f"{field} = ?" for field in update_fields.keys()]
                )
                values = list(update_fields.values()) + [category_id]

                cursor.execute(
                    f"UPDATE categories SET {set_clause} WHERE id = ?", values
                )

            return {
                "success": True,
                "message": f"カテゴリー '{existing[1]}' を更新しました",
                "updated_fields": list(update_fields.keys()),
            }

        except DataValidationError as e:
            return {"success": False, "error": "VALIDATION_ERROR", "message": e.message}
        except Exception as e:
            logger.error("Failed to update category: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "カテゴリーの更新に失敗しました",
            }

    def delete_category(self, category_id: int) -> Dict[str, Any]:
        """カテゴリーを削除.

        Args:
            category_id: カテゴリーID

        Returns:
            削除結果
        """
        try:
            # カテゴリーの存在確認
            existing = self.db_connection.execute_query(
                "SELECT id, name FROM categories WHERE id = ?",
                (category_id,),
                fetch_one=True,
            )

            if not existing:
                return {
                    "success": False,
                    "error": "NOT_FOUND",
                    "message": f"カテゴリーID {category_id} が見つかりません",
                }

            # 使用中かチェック（取引で使用されているか）
            transaction_count = self.db_connection.execute_query(
                "SELECT COUNT(*) FROM transactions WHERE category_id = ?",
                (category_id,),
                fetch_one=True,
            )

            if transaction_count and transaction_count[0] > 0:
                return {
                    "success": False,
                    "error": "CATEGORY_IN_USE",
                    "message": f"カテゴリー '{existing[1]}' は取引で使用されているため削除できません",
                }

            # 子カテゴリーの存在確認
            child_count = self.db_connection.execute_query(
                "SELECT COUNT(*) FROM categories WHERE parent_id = ?",
                (category_id,),
                fetch_one=True,
            )

            if child_count and child_count[0] > 0:
                return {
                    "success": False,
                    "error": "HAS_CHILDREN",
                    "message": f"カテゴリー '{existing[1]}' には子カテゴリーがあるため削除できません",
                }

            # カテゴリー削除
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))

            return {
                "success": True,
                "message": f"カテゴリー '{existing[1]}' を削除しました",
            }

        except Exception as e:
            logger.error("Failed to delete category: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "カテゴリーの削除に失敗しました",
            }


# グローバルなCategoryManagerインスタンス
_category_manager: Optional[CategoryManager] = None


def get_category_manager() -> CategoryManager:
    """CategoryManagerのシングルトンインスタンスを取得."""
    global _category_manager

    if _category_manager is None:
        _category_manager = CategoryManager()

    return _category_manager


class AccountManager:
    """アカウント管理クラス."""

    def __init__(self, db_connection: Optional[DatabaseConnection] = None):
        """AccountManager初期化.

        Args:
            db_connection: データベース接続オブジェクト。Noneの場合はデフォルトを使用
        """
        self.db_connection = db_connection or get_database_connection()

    def add_account(
        self,
        name: str,
        account_type: str,
        initial_balance: float = 0.0,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        """新しいアカウントを追加.

        Args:
            name: アカウント名（例：普通預金、給与口座、現金）
            account_type: アカウント種別（bank, cash, credit, investment）
            initial_balance: 初期残高
            is_active: アクティブ状態

        Returns:
            追加結果
        """
        try:
            # バリデーション
            if not name or not name.strip():
                return {
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "アカウント名は必須です",
                }

            if account_type not in ["bank", "cash", "credit", "investment"]:
                return {
                    "success": False,
                    "error": "VALIDATION_ERROR",
                    "message": "アカウント種別は bank, cash, credit, investment のいずれかである必要があります",
                }

            # 重複チェック
            existing = self.db_connection.execute_query(
                "SELECT id FROM accounts WHERE name = ?",
                (name.strip(),),
                fetch_one=True,
            )

            if existing:
                return {
                    "success": False,
                    "error": "DUPLICATE_NAME",
                    "message": f"アカウント名 '{name.strip()}' は既に存在します",
                }

            # アカウント追加
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    """INSERT INTO accounts (name, type, initial_balance,
                    current_balance, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)"""
                                                                                        ,
                    (
                        name.strip(),
                        account_type,
                        initial_balance,
                        initial_balance,
                        is_active,
                        datetime.now(),
                    ),
                )
                account_id = cursor.lastrowid

            return {
                "success": True,
                "message": f"アカウント '{name.strip()}' を追加しました",
                "account_id": account_id,
            }

        except Exception as e:
            logger.error("Failed to add account: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "アカウントの追加に失敗しました",
            }

    def get_accounts(
        self, account_type: Optional[str] = None, is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """アカウント一覧を取得.

        Args:
            account_type: アカウント種別でフィルタ
            is_active: アクティブ状態でフィルタ

        Returns:
            アカウント一覧
        """
        try:
            query = "SELECT * FROM accounts WHERE 1=1"
            params = []

            if account_type:
                query += " AND type = ?"
                params.append(account_type)

            if is_active is not None:
                query += " AND is_active = ?"
                params.append(is_active)

            query += " ORDER BY created_at DESC"

            results = self.db_connection.execute_query(query, tuple(params))

            if not results:
                return []

            accounts = []
            for row in results:
                accounts.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "initial_balance": float(row[3]),
                        "current_balance": float(row[4]),
                        "currency": row[5],
                        "is_active": bool(row[6]),
                        "created_at": row[7].isoformat() if row[7] else None,
                        "updated_at": row[8].isoformat() if row[8] else None,
                    }
                )

            return accounts

        except Exception as e:
            logger.error("Failed to get accounts: %s", e)
            return []

    def get_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        """指定IDのアカウントを取得.

        Args:
            account_id: アカウントID

        Returns:
            アカウント情報（見つからない場合はNone）
        """
        try:
            result = self.db_connection.execute_query(
                "SELECT * FROM accounts WHERE id = ?", (account_id,), fetch_one=True
            )

            if not result:
                return None

            return {
                "id": result[0],
                "name": result[1],
                "type": result[2],
                "initial_balance": float(result[3]),
                "current_balance": float(result[4]),
                "currency": result[5],
                "is_active": bool(result[6]),
                "created_at": result[7].isoformat() if result[7] else None,
                "updated_at": result[8].isoformat() if result[8] else None,
            }

        except Exception as e:
            logger.error("Failed to get account: %s", e)
            return None

    def update_account(
        self,
        account_id: int,
        name: Optional[str] = None,
        account_type: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """アカウント情報を更新.

        Args:
            account_id: アカウントID
            name: 新しいアカウント名
            account_type: 新しいアカウント種別
            is_active: 新しいアクティブ状態

        Returns:
            更新結果
        """
        try:
            # アカウントの存在確認
            existing = self.db_connection.execute_query(
                "SELECT id, name FROM accounts WHERE id = ?",
                (account_id,),
                fetch_one=True,
            )

            if not existing:
                return {
                    "success": False,
                    "error": "NOT_FOUND",
                    "message": f"アカウントID {account_id} が見つかりません",
                }

            # 更新フィールドの準備
            update_fields = {}

            if name is not None:
                if not name.strip():
                    return {
                        "success": False,
                        "error": "VALIDATION_ERROR",
                        "message": "アカウント名は必須です",
                    }

                # 名前の重複チェック（自分以外）
                name_check = self.db_connection.execute_query(
                    "SELECT id FROM accounts WHERE name = ? AND id != ?",
                    (name.strip(), account_id),
                    fetch_one=True,
                )

                if name_check:
                    return {
                        "success": False,
                        "error": "DUPLICATE_NAME",
                        "message": f"アカウント名 '{name.strip()}' は既に存在します",
                    }

                update_fields["name"] = name.strip()

            if account_type is not None:
                if account_type not in ["bank", "cash", "credit", "investment"]:
                    return {
                        "success": False,
                        "error": "VALIDATION_ERROR",
                        "message": "アカウント種別は bank, cash, credit, investment のいずれかである必要があります",
                    }
                update_fields["type"] = account_type

            if is_active is not None:
                update_fields["is_active"] = is_active

            if not update_fields:
                return {
                    "success": False,
                    "error": "NO_CHANGES",
                    "message": "更新する項目がありません",
                }

            # 更新日時を追加
            update_fields["updated_at"] = datetime.now()

            # アカウント更新
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()

                set_clause = ", ".join(
                    [f"{field} = ?" for field in update_fields.keys()]
                )
                values = list(update_fields.values()) + [account_id]

                cursor.execute(f"UPDATE accounts SET {set_clause} WHERE id = ?", values)

            return {
                "success": True,
                "message": f"アカウント '{existing[1]}' を更新しました",
                "updated_fields": list(update_fields.keys()),
            }

        except Exception as e:
            logger.error("Failed to update account: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "アカウントの更新に失敗しました",
            }

    def delete_account(self, account_id: int) -> Dict[str, Any]:
        """アカウントを削除.

        Args:
            account_id: アカウントID

        Returns:
            削除結果
        """
        try:
            # アカウントの存在確認
            existing = self.db_connection.execute_query(
                "SELECT id, name FROM accounts WHERE id = ?",
                (account_id,),
                fetch_one=True,
            )

            if not existing:
                return {
                    "success": False,
                    "error": "NOT_FOUND",
                    "message": f"アカウントID {account_id} が見つかりません",
                }

            # 使用中かチェック（取引で使用されているか）
            transaction_count = self.db_connection.execute_query(
                "SELECT COUNT(*) FROM transactions WHERE account_id = ?",
                (account_id,),
                fetch_one=True,
            )

            if transaction_count and transaction_count[0] > 0:
                return {
                    "success": False,
                    "error": "ACCOUNT_IN_USE",
                    "message": f"アカウント '{existing[1]}' は取引で使用されているため削除できません",
                }

            # アカウント削除
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()
                cursor.execute("DELETE FROM accounts WHERE id = ?", (account_id,))

            return {
                "success": True,
                "message": f"アカウント '{existing[1]}' を削除しました",
            }

        except Exception as e:
            logger.error("Failed to delete account: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "アカウントの削除に失敗しました",
            }

    def update_balance(self, account_id: int, new_balance: float) -> Dict[str, Any]:
        """アカウント残高を更新.

        Args:
            account_id: アカウントID
            new_balance: 新しい残高

        Returns:
            更新結果
        """
        try:
            # アカウントの存在確認
            existing = self.db_connection.execute_query(
                "SELECT id, name, current_balance FROM accounts WHERE id = ?",
                (account_id,),
                fetch_one=True,
            )

            if not existing:
                return {
                    "success": False,
                    "error": "NOT_FOUND",
                    "message": f"アカウントID {account_id} が見つかりません",
                }

            old_balance = existing[2]

            # 残高更新
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    "UPDATE accounts SET current_balance = ?, updated_at = ? WHERE id = ?",
                    (new_balance, datetime.now(), account_id),
                )

            # 型を統一してfloatに変換
            old_balance_float = float(old_balance) if old_balance is not None else 0.0

            return {
                "success": True,
                "message": f"アカウント '{existing[1]}' の残高を更新しました",
                "old_balance": old_balance_float,
                "new_balance": new_balance,
                "difference": new_balance - old_balance_float,
            }

        except Exception as e:
            logger.error("Failed to update account balance: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "残高の更新に失敗しました",
            }


# グローバルなAccountManagerインスタンス
_account_manager: Optional[AccountManager] = None


def get_account_manager() -> AccountManager:
    """AccountManagerのシングルトンインスタンスを取得."""
    global _account_manager

    if _account_manager is None:
        _account_manager = AccountManager()

    return _account_manager
