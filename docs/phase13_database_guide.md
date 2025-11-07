# Phase 13: SQLiteデータベース統合ガイド

## 概要

Phase 13では、既存のCSV ベースのデータ管理から SQLite データベース統合への移行を実施しました。このドキュメントでは、実装された機能、設計、および使用方法を説明します。

## 目次

- [データベーススキーマ](#データベーススキーマ)
- [API エンドポイント](#api-エンドポイント)
- [トランザクション管理](#トランザクション管理)
- [クエリ最適化](#クエリ最適化)
- [互換性レイヤー](#互換性レイヤー)
- [使用例](#使用例)

## データベーススキーマ

### 1. transactions テーブル

取引データを格納するメインテーブル。CSV から自動マイグレーション可能です。

**カラム定義:**

| カラム名             | 型       | 説明               | 制約                        |
| -------------------- | -------- | ------------------ | --------------------------- |
| id                   | Integer  | プライマリキー     | PRIMARY KEY, AUTO_INCREMENT |
| source_file          | String   | ソースCSVファイル  | NOT NULL, INDEXED           |
| row_number           | Integer  | CSV内の行番号      | NOT NULL, INDEXED           |
| date                 | Date     | 取引日             | NOT NULL, INDEXED           |
| amount               | Float    | 取引金額           | NOT NULL                    |
| description          | String   | 取引説明           | NULLABLE                    |
| category_major       | String   | 大分類カテゴリ     | NOT NULL, INDEXED           |
| category_minor       | String   | 小分類カテゴリ     | NULLABLE, INDEXED           |
| account              | String   | 口座名             | NULLABLE                    |
| memo                 | String   | メモ               | NULLABLE                    |
| is_target            | Integer  | 対象フラグ (0/1)   | DEFAULT 1                   |
| is_duplicate         | Integer  | 重複フラグ (0/1)   | DEFAULT 0                   |
| duplicate_of         | Integer  | 重複元の取引 ID    | NULLABLE                    |
| duplicate_checked    | Integer  | 重複確認済み (0/1) | DEFAULT 0                   |
| duplicate_checked_at | DateTime | 重複確認日時       | NULLABLE                    |
| created_at           | DateTime | 作成日時           | DEFAULT CURRENT_TIMESTAMP   |
| updated_at           | DateTime | 更新日時           | DEFAULT CURRENT_TIMESTAMP   |

**インデックス:**

```sql
-- 存在するインデックス
CREATE UNIQUE INDEX idx_source_file_row
  ON transactions(source_file, row_number);

CREATE INDEX idx_date_amount
  ON transactions(date, amount);

CREATE INDEX idx_date_range
  ON transactions(date);

-- 推奨インデックス（TASK-1306で定義）
CREATE INDEX idx_transaction_category_month
  ON transactions(category_major, category_minor, date);

CREATE INDEX idx_transaction_date_amount
  ON transactions(date, amount);
```

### 2. assets テーブル

資産情報（株、投資信託など）を管理するテーブル。

**カラム定義:**

| カラム名       | 型       | 説明             | 制約                        |
| -------------- | -------- | ---------------- | --------------------------- |
| id             | Integer  | プライマリキー   | PRIMARY KEY, AUTO_INCREMENT |
| asset_class_id | Integer  | 資産分類 ID      | NOT NULL, FOREIGN KEY       |
| date           | Date     | 記録日           | NOT NULL, INDEXED           |
| amount         | Float    | 資産額           | NOT NULL                    |
| quantity       | Float    | 数量             | NULLABLE                    |
| unit_price     | Float    | 単価             | NULLABLE                    |
| description    | String   | 説明             | NULLABLE                    |
| is_active      | Integer  | 有効フラグ (0/1) | DEFAULT 1                   |
| created_at     | DateTime | 作成日時         | DEFAULT CURRENT_TIMESTAMP   |
| updated_at     | DateTime | 更新日時         | DEFAULT CURRENT_TIMESTAMP   |

### 3. asset_classes テーブル

資産の分類（株式、投信、不動産など）を定義。

**カラム定義:**

| カラム名    | 型       | 説明           | 制約                        |
| ----------- | -------- | -------------- | --------------------------- |
| id          | Integer  | プライマリキー | PRIMARY KEY, AUTO_INCREMENT |
| name        | String   | 分類名         | NOT NULL, UNIQUE            |
| description | String   | 説明           | NULLABLE                    |
| created_at  | DateTime | 作成日時       | DEFAULT CURRENT_TIMESTAMP   |

**デフォルト分類:**

- 株式
- 投資信託
- 不動産
- 現金
- 銀行口座
- その他

### 4. category_hierarchy テーブル

カテゴリの階層構造を管理（主に参照用）。

| カラム名 | 型      | 説明           |
| -------- | ------- | -------------- |
| id       | Integer | プライマリキー |
| major    | String  | 大分類         |
| minor    | String  | 小分類         |

### 5. schema_versions テーブル

データベーススキーマのバージョン管理。

| カラム名   | 型       | 説明           |
| ---------- | -------- | -------------- |
| id         | Integer  | プライマリキー |
| version    | String   | バージョン番号 |
| applied_at | DateTime | 適用日時       |

### 6. migration_logs テーブル

CSV→SQLite マイグレーション履歴。

| カラム名         | 型       | 説明                 |
| ---------------- | -------- | -------------------- |
| id               | Integer  | プライマリキー       |
| source_file      | String   | ソースファイル       |
| total_records    | Integer  | 総レコード数         |
| imported_records | Integer  | インポート数         |
| skipped_records  | Integer  | スキップ数           |
| migrated_at      | DateTime | マイグレーション日時 |

## API エンドポイント

### 取引 (Transactions)

#### 作成

```http
POST /api/transactions/create

Content-Type: application/json
{
  "date": "2025-11-08T00:00:00",
  "amount": 1000.0,
  "description": "テスト取引",
  "category_major": "食費",
  "category_minor": "外食",
  "account": "クレジットカード",
  "memo": "テストメモ",
  "is_target": 1
}

Response (201 Created):
{
  "id": 11507,
  "source_file": "api",
  "row_number": 9999,
  "date": "2025-11-08",
  "amount": 1000.0,
  "category_major": "食費",
  "category_minor": "外食",
  ...
}
```

#### 一覧取得

```http
GET /api/transactions/list?category_major=食費&limit=20&offset=0

Response (200 OK):
[
  {
    "id": 1,
    "date": "2022-01-01",
    "amount": -1500.0,
    "category_major": "食費",
    ...
  },
  ...
]
```

#### 詳細取得

```http
GET /api/transactions/{id}

Response (200 OK):
{
  "id": 1,
  "date": "2022-01-01",
  "amount": -1500.0,
  ...
}
```

#### 更新

```http
PUT /api/transactions/{id}

Content-Type: application/json
{
  "amount": 2000.0,
  "description": "更新後の説明"
}

Response (200 OK):
{
  "id": 1,
  "amount": 2000.0,
  ...
}
```

#### 削除

```http
DELETE /api/transactions/{id}

Response (204 No Content)
```

### 資産 (Assets)

#### 分類一覧取得

```http
GET /api/assets/classes

Response (200 OK):
[
  {
    "id": 1,
    "name": "株式",
    "description": "日本株式"
  },
  ...
]
```

#### 資産レコード作成

```http
POST /api/assets/records/create

Content-Type: application/json
{
  "asset_class_id": 1,
  "date": "2025-11-08",
  "amount": 100000.0,
  "quantity": 100,
  "unit_price": 1000.0,
  "description": "テスト株式"
}

Response (201 Created):
{
  "id": 1,
  "asset_class_id": 1,
  "date": "2025-11-08",
  "amount": 100000.0,
  ...
}
```

#### 資産レコード一覧

```http
GET /api/assets/records?asset_class_id=1&limit=20

Response (200 OK):
[
  {...},
  ...
]
```

#### 資産レコード詳細

```http
GET /api/assets/records/{id}
```

#### 資産レコード更新

```http
PUT /api/assets/records/{id}
```

#### 資産レコード削除

```http
DELETE /api/assets/records/{id}
```

## トランザクション管理

### 基本的な使用方法

```python
from household_mcp.database.transaction_manager import TransactionManager

tm = TransactionManager()

# Session スコープの使用
with tm.session_scope() as session:
    tx = Transaction(
        source_file="api",
        row_number=10000,
        date=datetime.now(),
        amount=-1000,
        category_major="食費",
        category_minor="外食",
        description="新規取引"
    )
    session.add(tx)
    # コミットは自動的に実行される
```

### リトライ機構

```python
# 自動リトライ付きでトランザクション実行
def add_transaction(session):
    tx = Transaction(...)
    session.add(tx)
    return tx

result = tm.execute_in_transaction(add_transaction)

# カスタムリトライ設定
from household_mcp.database.transaction_manager import RetryConfig

config = RetryConfig(
    max_retries=5,
    backoff_ms=100,
    backoff_multiplier=2.0  # 指数バックオフ
)

result = tm.execute_in_transaction(
    add_transaction,
    retry_config=config
)
```

### エラーハンドリング

```python
from household_mcp.database.transaction_manager import (
    TransactionError,
    TransactionManager
)

tm = TransactionManager()

try:
    with tm.session_scope() as session:
        # ... トランザクション処理
        pass
except TransactionError as e:
    # ロールバック済みの状態で例外が発生
    logger.error(f"トランザクション失敗: {e}")
    # 再試行またはユーザーへの通知
```

## クエリ最適化

### QueryOptimizer の使用

```python
from household_mcp.database.query_optimization import QueryOptimizer

optimizer = QueryOptimizer(session)

# クエリプラン分析
plan = optimizer.analyze_query_plan(
    "SELECT * FROM transactions WHERE date = '2024-01-01'"
)
print(f"使用インデックス: {plan.use_indexes}")
print(f"推奨: {plan.recommendation}")

# インデックス戦略の提案
strategies = optimizer.get_index_strategies()
for strategy in strategies:
    print(f"{strategy.index_name}: {strategy.reason}")

# テーブル統計
stats = optimizer.get_table_stats()
for table, info in stats.items():
    print(f"{table}: {info['record_count']} records")
```

### AggregationOptimizer の使用

```python
from household_mcp.database.query_optimization import AggregationOptimizer

agg_opt = AggregationOptimizer(session)

# 月次カテゴリ別集計
df = agg_opt.get_monthly_category_summary(2024, 1)

# 日付範囲の集計
from datetime import datetime
start = datetime(2024, 1, 1)
end = datetime(2024, 12, 31)
df = agg_opt.get_date_range_summary(start, end)

# トップカテゴリ
df = agg_opt.get_top_categories(limit=10)
```

### IndexManager の使用

```python
from household_mcp.database.query_optimization import IndexManager

index_mgr = IndexManager(session)

# インデックス作成
index_mgr.create_index(
    "idx_transaction_category_month",
    "transactions",
    ["category_major", "category_minor", "date"],
    is_unique=False
)

# インデックス情報の取得
indexes = index_mgr.get_existing_indexes()

# 統計情報の更新
index_mgr.analyze_statistics()

# データベース最適化
index_mgr.vacuum()
```

## 互換性レイヤー

### DataLoaderAdapter の使用

既存の CSV ローダと SQLite ベースの実装を透過的に切り替え可能。

```python
from household_mcp.dataloader_compat import DataLoaderAdapter

# CSV バックエンド（既存の動作を継続）
adapter = DataLoaderAdapter(backend="csv")
df = adapter.load_month(2024, 1)

# SQLite バックエンド（新規）
adapter = DataLoaderAdapter(backend="sqlite")
df = adapter.load_month(2024, 1)  # 同じインターフェース

# 利用可能月の取得
months = adapter.get_available_months()

# カテゴリ階層の取得
categories = adapter.get_category_hierarchy()

# キャッシュ統計
stats = adapter.get_cache_stats()
print(f"ヒット率: {stats['hit_rate']:.1%}")
```

## 使用例

### 完全な取引追加フロー

```python
from household_mcp.database.transaction_manager import TransactionManager
from household_mcp.database import Transaction
from datetime import datetime

tm = TransactionManager()

def add_income(session):
    """給料の記録"""
    tx = Transaction(
        source_file="manual",
        row_number=99999,
        date=datetime(2025, 11, 8),
        amount=250000,  # 給料は正の金額
        category_major="収入",
        category_minor="給料",
        account="銀行口座",
        description="11月分給料",
        is_target=1
    )
    session.add(tx)
    return tx

try:
    result = tm.execute_in_transaction(add_income)
    print(f"取引を作成しました: ID={result.id}")
except Exception as e:
    print(f"エラー: {e}")
    # ロールバック済み
```

### 月次集計レポート

```python
from household_mcp.database.query_optimization import AggregationOptimizer
from household_mcp.database.manager import DatabaseManager

db = DatabaseManager()
session = db.get_session()

agg = AggregationOptimizer(session)

# 11月の月次集計
df = agg.get_monthly_category_summary(2025, 11)
print(df)

# トップ10支出カテゴリ
top = agg.get_top_categories(limit=10)
print(f"\nトップ10:\n{top}")

session.close()
```

## トラブルシューティング

### no such table: transactions

**原因**: データベースが初期化されていない

**解決方法**:

```python
from household_mcp.database.manager import DatabaseManager

db = DatabaseManager()
db.initialize_database()  # スキーマ作成
db.initialize_database(migrate_csv=True)  # CSV マイグレーション
```

### UNIQUE constraint failed

**原因**: 同じ source_file と row_number の組み合わせが既に存在

**解決方法**: 別の source_file を使用するか、重複チェックを行う

### column X not found

**原因**: モデルに定義されていないカラムへのアクセス

**解決方法**: モデル定義を確認し、正しいカラム名を使用

## 関連ドキュメント

- [requirements.md](../requirements.md) - Phase 13 要件定義
- [design.md](../design.md) - Phase 13 技術設計
- [tasks.md](../tasks.md) - Phase 13 タスク計画
