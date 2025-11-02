"""家計簿データ管理ツール.

取引、カテゴリー、アカウントのCRUD操作を提供
"""

import logging
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..database.connection import DatabaseConnection
from ..exceptions import ValidationError

# ロガー設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TransactionManager:
    """取引データ管理クラス."""

    def __init__(self) -> None:
        """初期化."""
        self.db_connection = DatabaseConnection()

    def add_transaction(
        self,
        date: str,
        amount: float,
        description: str,
        category_name: str,
        account_name: str,
        transaction_type: str,
    ) -> Dict[str, Any]:
        """新しい取引を追加.

        Args:
            date: 日付
            amount: 金額
            description: 説明
            category_name: カテゴリー名
            account_name: アカウント名
            transaction_type: 取引タイプ ('income' or 'expense')

        Returns:
            追加された取引の情報
        """
        try:
            # logger.info("Attempting to add transaction with data: %s", locals())
            self._validate_transaction_data(
                date, amount, description, category_name, account_name, transaction_type
            )

            with self.db_connection.transaction() as conn:
                category_id = self._get_category_id(category_name, transaction_type)
                account_id = self._get_account_id(account_name)

                insert_query = """
                    INSERT INTO transactions (date, amount, description, category_id, account_id, type)
                    VALUES (?, ?, ?, ?, ?, ?)
                """
                params = (
                    date,
                    float(amount),
                    description,
                    category_id,
                    account_id,
                    transaction_type,
                )

                cursor = conn.cursor()
                cursor.execute(insert_query, params)
                transaction_id = cursor.lastrowid

                self._update_account_balance(conn, account_id, amount, transaction_type)

            logger.info("Transaction added successfully: ID=%s", transaction_id)
            return {
                "success": True,
                "transaction_id": transaction_id,
                "message": "取引が正常に追加されました",
            }
        except ValidationError as e:
            logger.warning("Data validation error: %s", e)
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error("Failed to add transaction: %s", e)
            # トランザクションの追加に失敗した場合、より詳細なエラー情報を提供
            return {
                "success": False,
                "error": f"予期せぬエラーが発生しました: {e}",
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
        """取引一覧を取得."""
        try:
            conditions, params = self._build_query_conditions(
                start_date, end_date, category_name, account_name, transaction_type
            )
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            transactions = self._fetch_transactions(where_clause, params, limit, offset)
            total_count = self._get_total_transaction_count(where_clause, params)

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

    def _build_query_conditions(
        self,
        start_date: Optional[str],
        end_date: Optional[str],
        category_name: Optional[str],
        account_name: Optional[str],
        transaction_type: Optional[str],
    ) -> tuple[list[str], list[Any]]:
        conditions: list[str] = []
        params: list[Any] = []
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
        return conditions, params

    def _fetch_transactions(
        self, where_clause: str, params: list[Any], limit: int, offset: int
    ) -> list[dict[str, Any]]:
        # Bandit: where_clause is internally constructed from parameterized conditions; no user-supplied identifiers
        # nosec B608
        query = (
            "SELECT\n"
            "    t.id, t.date, t.amount, t.description, t.type,\n"
            "    c.name as category_name, a.name as account_name,\n"
            "    t.created_at, t.updated_at\n"
            "FROM transactions t\n"
            "LEFT JOIN categories c ON t.category_id = c.id\n"
            "LEFT JOIN accounts a ON t.account_id = a.id\n"
            f"{where_clause}\n"
            "ORDER BY t.date DESC, t.id DESC\n"
            "LIMIT ? OFFSET ?\n"
        )  # nosec B608: where_clause is built from whitelisted fields; parameters are bound
        query_params = tuple(params + [limit, offset])
        result = self.db_connection.execute_query(query, query_params, fetch_all=True)

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
        return transactions

    def _get_total_transaction_count(self, where_clause: str, params: list[Any]) -> int:
        # Bandit: where_clause is internally constructed from parameterized conditions; no user-supplied identifiers
        # nosec B608
        count_query = (
            "SELECT COUNT(*) FROM transactions t\n"
            "LEFT JOIN categories c ON t.category_id = c.id\n"
            "LEFT JOIN accounts a ON t.account_id = a.id\n"
            f"{where_clause}\n"
        )  # nosec B608: safe dynamic clause from validated fields
        count_result = self.db_connection.execute_query(
            count_query, tuple(params), fetch_one=True
        )
        return count_result[0] if count_result else 0

    def update_transaction(self, transaction_id: int, **kwargs: Any) -> Dict[str, Any]:
        """取引を更新."""
        try:
            existing = self._get_transaction_by_id(transaction_id)
            if not existing:
                return {
                    "success": False,
                    "error": "Transaction not found",
                    "message": f"ID {transaction_id} の取引が見つかりません",
                }

            update_fields, update_params = self._prepare_transaction_update(
                existing, **kwargs
            )

            if not update_fields:
                return {
                    "success": False,
                    "error": "No valid fields to update",
                    "message": "更新対象のフィールドがありません",
                }

            self._execute_transaction_update(
                transaction_id, update_fields, update_params
            )

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

    def _prepare_transaction_update(
        self, existing_transaction: Dict[str, Any], **kwargs: Any
    ) -> tuple[list[str], list[Any]]:
        allowed_fields = [
            "date",
            "amount",
            "description",
            "category_name",
            "account_name",
        ]
        update_fields: list[str] = []
        update_params: list[Any] = []

        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                if field == "date":
                    update_fields.append("date = ?")
                    update_params.append(datetime.strptime(value, "%Y-%m-%d").date())
                elif field == "amount":
                    update_fields.append("amount = ?")
                    update_params.append(float(value))
                elif field == "description":
                    update_fields.append("description = ?")
                    update_params.append(value)
                elif field == "category_name":
                    category_id = self._get_category_id(
                        value, existing_transaction["type"]
                    )
                    update_fields.append("category_id = ?")
                    update_params.append(category_id)
                elif field == "account_name":
                    account_id = self._get_account_id(value)
                    update_fields.append("account_id = ?")
                    update_params.append(account_id)
        return update_fields, update_params

    def _execute_transaction_update(
        self, transaction_id: int, update_fields: list[str], update_params: list[Any]
    ) -> None:
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        update_params.append(transaction_id)

        # Bandit: update_fields are pre-validated field names from allowed list
        # nosec B608
        query = f"UPDATE transactions\nSET {', '.join(update_fields)}\nWHERE id = ?\n"  # nosec B608: update_fields are whitelisted column names

        with self.db_connection.transaction() as conn:
            cursor = conn.cursor()
            cursor.execute(query, tuple(update_params))
            if cursor.rowcount == 0:
                raise Exception("取引の更新に失敗しました")

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
        transaction_type: str,
    ) -> None:
        """取引データの検証."""
        if not date:
            raise ValidationError("日付は必須です")

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise ValidationError("日付はYYYY-MM-DD形式で入力してください")

        if amount is None or amount <= 0:
            raise ValidationError("金額は正の数値である必要があります")

        if not description or not description.strip():
            raise ValidationError("説明は必須です")

        if transaction_type not in ["income", "expense"]:
            raise ValidationError(
                "取引タイプは 'income' または 'expense' である必要があります"
            )

        if not category_name or not category_name.strip():
            raise ValidationError("カテゴリー名は必須です")

        if not account_name or not account_name.strip():
            raise ValidationError("アカウント名は必須です")

    def _get_category_id(self, category_name: str, transaction_type: str) -> int:
        """カテゴリーIDを取得、存在しない場合は作成.

        Args:
            category_name: カテゴリー名
            transaction_type: 取引タイプ

        Returns:
            カテゴリーID
        """
        query = "SELECT id FROM categories WHERE name = ? AND type = ?"
        result = self.db_connection.execute_query(
            query, (category_name, transaction_type), fetch_one=True
        )
        if result:
            return int(result[0])
        else:
            # カテゴリーが存在しない場合は新規作成
            insert_query = "INSERT INTO categories (name, type) VALUES (?, ?)"
            with self.db_connection.transaction() as conn:
                cursor = conn.cursor()
                cursor.execute(insert_query, (category_name, transaction_type))
                category_id = cursor.lastrowid
                if category_id is None:
                    raise ValidationError("カテゴリーの作成に失敗しました")
                return category_id

    def _get_account_id(self, account_name: str) -> int:
        """アカウントIDを取得（存在しない場合はエラー）."""
        query = "SELECT id FROM accounts WHERE name = ?"
        result = self.db_connection.execute_query(
            query, (account_name,), fetch_one=True
        )

        if result:
            return int(result[0])

        raise ValidationError(f"アカウント '{account_name}' が見つかりません")

    def _update_account_balance(
        self,
        conn: sqlite3.Connection,
        account_id: int,
        amount: float,
        transaction_type: str,
    ) -> None:
        """アカウント残高を更新.

        Args:
            conn: データベース接続
            account_id: アカウントID
            amount: 金額
            transaction_type: 取引タイプ
        """
        if transaction_type == "income":
            update_query = (
                "UPDATE accounts SET current_balance = current_balance + ? WHERE id = ?"
            )
        else:
            update_query = (
                "UPDATE accounts SET current_balance = current_balance - ? WHERE id = ?"
            )

        cursor = conn.cursor()
        cursor.execute(update_query, (float(amount), account_id))

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

    def __init__(self) -> None:
        """初期化."""
        self.db_connection = DatabaseConnection()

    def get_categories(self, category_type: Optional[str] = None) -> Dict[str, Any]:
        """カテゴリー一覧を取得.

        Args:
            category_type: カテゴリータイプ ('income' または 'expense')

        Returns:
            カテゴリー一覧
        """
        try:
            query = "SELECT id, name, type, parent_id, color, icon FROM categories"
            params: list[Any] = []

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
                raise ValidationError(
                    "カテゴリータイプは 'income' または 'expense' である必要があります"
                )

            if not name or not name.strip():
                raise ValidationError("カテゴリー名は必須です")

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
                    VALUES (?, ?, ?, ?, ?)""",
                    (name.strip(), category_type, parent_id, color, icon),
                )

                category_id = cursor.lastrowid

            return {
                "success": True,
                "message": f"カテゴリー '{name}' を追加しました",
                "category_id": category_id,
            }

        except ValidationError as e:
            return {"success": False, "error": "VALIDATION_ERROR", "message": e.message}
        except Exception as e:
            logger.error("Failed to add category: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "カテゴリーの追加に失敗しました",
            }

    def update_category(self, category_id: int, **kwargs: Any) -> Dict[str, Any]:
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
                raise ValidationError(
                    "カテゴリータイプは 'income' または 'expense' である必要があります"
                )

            # 更新実行
            with self.db_connection.transaction() as connection:
                cursor = connection.cursor()

                set_clause = ", ".join(
                    [f"{field} = ?" for field in update_fields.keys()]
                )
                values = list(update_fields.values()) + [category_id]

                # Bandit: set_clause is derived from allowed field names; parameters remain bound
                cursor.execute(
                    f"UPDATE categories SET {set_clause} WHERE id = ?",
                    values,  # nosec B608
                )

            return {
                "success": True,
                "message": f"カテゴリー '{existing[1]}' を更新しました",
                "updated_fields": list(update_fields.keys()),
            }

        except ValidationError as e:
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
        self.db_connection = db_connection or DatabaseConnection()

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
                    current_balance, is_active, created_at) VALUES (?, ?, ?, ?, ?, ?)""",
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
            params: list[Any] = []

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
                # カラムインデックス: id, name, type, balance, initial_balance, current_balance, is_active, created_at, updated_at
                accounts.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "balance": float(row[3]) if row[3] is not None else 0.0,
                        "initial_balance": float(row[4]) if row[4] is not None else 0.0,
                        "current_balance": float(row[5]) if row[5] is not None else 0.0,
                        "is_active": bool(row[6]) if row[6] is not None else True,
                        "created_at": (
                            row[7]
                            if isinstance(row[7], str)
                            else (row[7].isoformat() if row[7] else None)
                        ),
                        "updated_at": (
                            row[8]
                            if isinstance(row[8], str)
                            else (row[8].isoformat() if row[8] else None)
                        ),
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

            # カラムインデックスに基づいて結果を返す
            # accounts: id, name, type, balance, initial_balance, current_balance, is_active, created_at
            return {
                "id": result[0],
                "name": result[1],
                "type": result[2],
                "balance": float(result[3]) if result[3] is not None else 0.0,
                "initial_balance": float(result[4]) if result[4] is not None else 0.0,
                "current_balance": float(result[5]) if result[5] is not None else 0.0,
                "is_active": bool(result[6]) if result[6] is not None else True,
                "created_at": (
                    result[7]
                    if isinstance(result[7], str)
                    else (result[7].isoformat() if result[7] else None)
                ),
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

            update_fields = self._prepare_account_update_fields(
                account_id, name, account_type, is_active
            )

            if not update_fields:
                return {
                    "success": False,
                    "error": "NO_CHANGES",
                    "message": "更新する項目がありません",
                }

            self._execute_account_update(account_id, update_fields)

            existing_name = None
            if existing and isinstance(existing, (list, tuple)) and len(existing) > 1:
                existing_name = existing[1]
            return {
                "success": True,
                "message": (
                    f"アカウント '{existing_name}' を更新しました"
                    if existing_name
                    else "アカウント情報を更新しました"
                ),
                "updated_fields": list(update_fields.keys()),
            }

        except ValidationError as e:
            return {"success": False, "error": "VALIDATION_ERROR", "message": str(e)}
        except Exception as e:
            logger.error("Failed to update account: %s", e)
            return {
                "success": False,
                "error": str(e),
                "message": "アカウントの更新に失敗しました",
            }

    def _prepare_account_update_fields(
        self,
        account_id: int,
        name: Optional[str],
        account_type: Optional[str],
        is_active: Optional[bool],
    ) -> Dict[str, Any]:
        update_fields: Dict[str, Any] = {}
        if name is not None:
            if not name.strip():
                raise ValidationError("アカウント名は必須です")
            name_check = self.db_connection.execute_query(
                "SELECT id FROM accounts WHERE name = ? AND id != ?",
                (name.strip(), account_id),
                fetch_one=True,
            )
            if name_check:
                raise ValidationError(f"アカウント名 '{name.strip()}' は既に存在します")
            update_fields["name"] = name.strip()

        if account_type is not None:
            if account_type not in ["bank", "cash", "credit", "investment"]:
                raise ValidationError(
                    "アカウント種別は bank, cash, credit, investment のいずれかである必要があります"
                )
            update_fields["type"] = account_type

        if is_active is not None:
            update_fields["is_active"] = is_active

        return update_fields

    def _execute_account_update(
        self, account_id: int, update_fields: Dict[str, Any]
    ) -> None:
        update_fields["updated_at"] = datetime.now()
        set_clause = ", ".join([f"{field} = ?" for field in update_fields.keys()])
        values = list(update_fields.values()) + [account_id]

        with self.db_connection.transaction() as connection:
            cursor = connection.cursor()
            # Bandit: set_clause is built from validated fields; values are parameterized
            cursor.execute(
                f"UPDATE accounts SET {set_clause} WHERE id = ?",
                values,  # nosec B608
            )

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

            # 関連する取引がないかチェック
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
