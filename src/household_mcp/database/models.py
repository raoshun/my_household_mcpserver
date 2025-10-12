"""家計簿分析MCPサーバー用データベースモデル.

SQLiteデータベースのテーブル定義とORM的な機能を提供
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """取引データモデル."""

    id: Optional[int] = None
    date: Optional[date_type] = None
    amount: Optional[Decimal] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    account_id: Optional[int] = None
    type: Optional[str] = None  # 'income' or 'expense'
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        """バリデーションと自動設定."""
        if self.type is not None and self.type not in ["income", "expense"]:
            raise ValueError("Type must be 'income' or 'expense'")


@dataclass
class Category:
    """カテゴリーデータモデル."""

    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None  # 'income' or 'expense'
    parent_id: Optional[int] = None
    color: Optional[str] = None
    icon: Optional[str] = None

    def __post_init__(self) -> None:
        """バリデーション."""
        if self.type is not None and self.type not in ["income", "expense"]:
            raise ValueError("Type must be 'income' or 'expense'")


@dataclass
class Account:
    """アカウントデータモデル."""

    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None  # 'bank', 'credit', 'cash', 'investment'
    initial_balance: Decimal = Decimal("0")
    current_balance: Decimal = Decimal("0")
    currency: str = "JPY"
    is_active: bool = True

    def __post_init__(self) -> None:
        """バリデーションと自動設定."""
        valid_types = ["bank", "credit", "cash", "investment"]
        if self.type is not None and self.type not in valid_types:
            raise ValueError(f"Type must be one of: {', '.join(valid_types)}")


@dataclass
class Budget:
    """予算データモデル."""

    id: Optional[int] = None
    category_id: Optional[int] = None
    amount: Optional[Decimal] = None
    period_type: Optional[str] = None  # 'monthly' or 'yearly'
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None

    def __post_init__(self) -> None:
        """バリデーション."""
        valid_periods = ["monthly", "yearly"]
        if self.period_type is not None and self.period_type not in valid_periods:
            raise ValueError(f"Period type must be one of: {', '.join(valid_periods)}")


class DatabaseSchema:
    """データベーススキーマ管理クラス."""

    # テーブル作成SQL文
    CREATE_TABLES_SQL = [
        """CREATE TABLE IF NOT EXISTS categories ( id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE, type TEXT CHECK(type IN ('income', 'expense')),
        parent_id INTEGER, color TEXT, icon TEXT,

        FOREIGN KEY (parent_id) REFERENCES categories(id) )
        """,
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT CHECK(type IN ('bank', 'credit', 'cash', 'investment')),
            initial_balance DECIMAL(10,2) DEFAULT 0,
            current_balance DECIMAL(10,2) DEFAULT 0,
            currency TEXT DEFAULT 'JPY',
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """CREATE TABLE IF NOT EXISTS transactions ( id INTEGER PRIMARY KEY
        AUTOINCREMENT, date DATE NOT NULL, amount DECIMAL(10,2) NOT NULL, description
        TEXT, category_id INTEGER, account_id INTEGER, type TEXT CHECK(type IN
        ('income', 'expense')), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (category_id)
        REFERENCES categories(id),

        FOREIGN KEY (account_id) REFERENCES accounts(id) )
        """,
        """
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            amount DECIMAL(10,2) NOT NULL,
            period_type TEXT CHECK(period_type IN ('monthly', 'yearly')),
            start_date DATE,
            end_date DATE,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
        """,
    ]

    # インデックス作成SQL文
    CREATE_INDEXES_SQL = [
        "CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_category ON transactions(category_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_id)",
        "CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type)",
    ]
    # デフォルトデータ挿入SQL文
    INSERT_DEFAULT_DATA_SQL = [
        """INSERT OR IGNORE INTO categories (name, type) VALUES ('食費', 'expense'),
        ('交通費', 'expense'), ('光熱費', 'expense'), ('娯楽費', 'expense'), ('医療費', 'expense'),
        ('教育費', 'expense'), ('給与', 'income'), ('副業', 'income'), ('投資収益', 'income')""",
        """
        INSERT OR IGNORE INTO accounts (name, type, initial_balance, current_balance) VALUES
        ('現金', 'cash', 0, 0),
        ('メイン銀行', 'bank', 0, 0)
        """,
    ]

    @classmethod
    def create_all_tables(cls, connection: sqlite3.Connection) -> None:
        """全テーブルとインデックスを作成."""
        try:
            cursor = connection.cursor()

            # 外部キー制約を有効化
            cursor.execute("PRAGMA foreign_keys = ON")

            # テーブル作成
            for sql in cls.CREATE_TABLES_SQL:
                cursor.execute(sql)

            # インデックス作成
            for sql in cls.CREATE_INDEXES_SQL:
                cursor.execute(sql)

            # デフォルトデータ挿入
            for sql in cls.INSERT_DEFAULT_DATA_SQL:
                cursor.execute(sql)

            connection.commit()
            logger.info("Database schema created successfully")

        except sqlite3.Error as e:
            connection.rollback()
            logger.error("Error creating database schema: %s", e)
            raise

    @classmethod
    def get_table_info(
        cls, connection: sqlite3.Connection, table_name: str
    ) -> List[Dict[str, Any]]:
        """テーブル情報の取得."""
        try:
            cursor = connection.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            return [
                {
                    "cid": col[0],
                    "name": col[1],
                    "type": col[2],
                    "notnull": bool(col[3]),
                    "default_value": col[4],
                    "primary_key": bool(col[5]),
                }
                for col in columns
            ]

        except sqlite3.Error as e:
            logger.error("Error getting table info for %s: %s", table_name, e)
            return []

    @classmethod
    def verify_schema(cls, connection: sqlite3.Connection) -> Dict[str, bool]:
        """スキーマの検証."""
        expected_tables = ["transactions", "categories", "accounts", "budgets"]
        results = {}

        try:
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]

            for table in expected_tables:
                results[table] = table in existing_tables

            return results

        except sqlite3.Error as e:
            logger.error("Error verifying schema: %s", e)
            return dict.fromkeys(expected_tables, False)


def decimal_adapter(value: Decimal) -> str:
    """Decimal型をSQLite用に変換."""
    return str(value)


def decimal_converter(value: bytes) -> Decimal:
    """SQLiteからDecimal型に変換."""
    return Decimal(value.decode())


def date_adapter(value: date_type) -> str:
    """date型をSQLite用に変換."""
    return value.isoformat()


def date_converter(value: bytes) -> date_type:
    """SQLiteからdate型に変換."""
    return datetime.strptime(value.decode(), "%Y-%m-%d").date()


def datetime_adapter(value: datetime) -> str:
    """datetime型をSQLite用に変換."""
    return value.isoformat()


def datetime_converter(value: bytes) -> datetime:
    """SQLiteからdatetime型に変換."""
    return datetime.fromisoformat(value.decode())


# SQLite型変換の登録
sqlite3.register_adapter(Decimal, decimal_adapter)
sqlite3.register_converter("DECIMAL", decimal_converter)
sqlite3.register_adapter(date_type, date_adapter)
sqlite3.register_converter("DATE", date_converter)
sqlite3.register_adapter(datetime, datetime_adapter)
sqlite3.register_converter("TIMESTAMP", datetime_converter)
