# 家計簿分析MCPサーバ 設計書

## 1. システムアーキテクチャ

### 1.1 全体アーキテクチャ

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AIエージェント  │◄──►│  MCPサーバー     │◄──►│  データベース    │
│   (Claude等)    │    │  (家計簿分析)    │    │  (SQLite)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  分析エンジン    │
                       │  (pandas,       │
                       │   matplotlib)   │
                       └─────────────────┘
```

### 1.2 MCPサーバーコンポーネント

- **接続管理**: AIエージェントとの通信
- **クエリ処理**: 自然言語の意図解析
- **データアクセス**: データベース操作
- **分析エンジン**: 統計・可視化処理
- **応答生成**: 結果の自然言語化

### 1.3 技術スタック

#### 1.3.1 開発環境

- **言語**: Python 3.11+
- **フレームワーク**: FastAPI (MCPサーバー)
- **データベース**: SQLite (開発), PostgreSQL (本番)
- **データ分析**: pandas, numpy, scipy
- **可視化**: matplotlib, plotly
- **テスト**: pytest, pytest-asyncio

#### 1.3.2 依存ライブラリ

```python
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
pandas==2.1.3
numpy==1.25.2
matplotlib==3.8.2
plotly==5.17.0
pydantic==2.5.0
python-dateutil==2.8.2
pytest==7.4.3
pytest-asyncio==0.21.1
mcp-python==0.1.0
```

## 2. データベース設計

### 2.1 ERD（Entity Relationship Diagram）

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   accounts      │    │  transactions   │    │   categories    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id (PK)         │◄──┤ account_id (FK) │    │ id (PK)         │
│ name            │    │ id (PK)         │◄──┤ name            │
│ type            │    │ date            │    │ type            │
│ initial_balance │    │ amount          │    │ parent_id (FK)  │
│ current_balance │    │ description     │    │ color           │
│ currency        │    │ category_id(FK) │    │ icon            │
│ is_active       │    │ type            │    └─────────────────┘
└─────────────────┘    │ created_at      │
                       │ updated_at      │
                       └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │    budgets      │
                       ├─────────────────┤
                       │ id (PK)         │
                       │ category_id(FK) │
                       │ amount          │
                       │ period_type     │
                       │ start_date      │
                       │ end_date        │
                       └─────────────────┘
```

### 2.2 テーブル定義

#### 2.2.1 取引テーブル (transactions)

```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    description TEXT,
    category_id INTEGER,
    account_id INTEGER,
    type TEXT CHECK(type IN ('income', 'expense')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

-- インデックス
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_category ON transactions(category_id);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_type ON transactions(type);
```

#### 2.2.2 カテゴリーテーブル (categories)

```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT CHECK(type IN ('income', 'expense')),
    parent_id INTEGER,
    color TEXT,
    icon TEXT,
    FOREIGN KEY (parent_id) REFERENCES categories(id)
);

-- デフォルトカテゴリーの挿入
INSERT INTO categories (name, type) VALUES
('食費', 'expense'),
('交通費', 'expense'),
('光熱費', 'expense'),
('娯楽費', 'expense'),
('給与', 'income'),
('副業', 'income');
```

#### 2.2.3 アカウントテーブル (accounts)

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT CHECK(type IN ('bank', 'credit', 'cash', 'investment')),
    initial_balance DECIMAL(10,2) DEFAULT 0,
    current_balance DECIMAL(10,2) DEFAULT 0,
    currency TEXT DEFAULT 'JPY',
    is_active BOOLEAN DEFAULT 1
);

-- デフォルトアカウントの挿入
INSERT INTO accounts (name, type, initial_balance, current_balance) VALUES
('現金', 'cash', 0, 0),
('メイン銀行', 'bank', 0, 0);
```

#### 2.2.4 予算テーブル (budgets)

```sql
CREATE TABLE budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER,
    amount DECIMAL(10,2) NOT NULL,
    period_type TEXT CHECK(period_type IN ('monthly', 'yearly')),
    start_date DATE,
    end_date DATE,
    FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

## 3. MCPツール設計

### 3.1 データ操作ツール

#### 3.1.1 add_transaction

```python
{
    "name": "add_transaction",
    "description": "新しい取引を追加",
    "inputSchema": {
        "type": "object",
        "properties": {
            "date": {"type": "string", "format": "date"},
            "amount": {"type": "number"},
            "description": {"type": "string"},
            "category": {"type": "string"},
            "account": {"type": "string"},
            "type": {"type": "string", "enum": ["income", "expense"]}
        },
        "required": ["date", "amount", "type"]
    }
}
```

#### 3.1.2 update_transaction

```python
{
    "name": "update_transaction",
    "description": "既存取引の更新",
    "inputSchema": {
        "type": "object",
        "properties": {
            "transaction_id": {"type": "integer"},
            "date": {"type": "string", "format": "date"},
            "amount": {"type": "number"},
            "description": {"type": "string"},
            "category": {"type": "string"},
            "account": {"type": "string"},
            "type": {"type": "string", "enum": ["income", "expense"]}
        },
        "required": ["transaction_id"]
    }
}
```

#### 3.1.3 get_transactions

```python
{
    "name": "get_transactions",
    "description": "取引データの取得",
    "inputSchema": {
        "type": "object",
        "properties": {
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "category": {"type": "string"},
            "account": {"type": "string"},
            "limit": {"type": "integer", "default": 100}
        }
    }
}
```

### 3.2 分析ツール

#### 3.2.1 analyze_spending_by_category

```python
{
    "name": "analyze_spending_by_category",
    "description": "カテゴリー別支出分析",
    "inputSchema": {
        "type": "object",
        "properties": {
            "period": {"type": "string", "enum": ["month", "year", "custom"]},
            "start_date": {"type": "string", "format": "date"},
            "end_date": {"type": "string", "format": "date"},
            "chart_type": {"type": "string", "enum": ["pie", "bar", "line"]}
        },
        "required": ["period"]
    }
}
```

#### 3.2.2 analyze_income_expense_trend

```python
{
    "name": "analyze_income_expense_trend",
    "description": "収支トレンド分析",
    "inputSchema": {
        "type": "object",
        "properties": {
            "period": {"type": "string"},
            "granularity": {"type": "string", "enum": ["daily", "weekly", "monthly"]}
        },
        "required": ["period"]
    }
}
```

#### 3.2.3 detect_anomalies

```python
{
    "name": "detect_anomalies",
    "description": "支出異常の検知",
    "inputSchema": {
        "type": "object",
        "properties": {
            "sensitivity": {"type": "string", "enum": ["low", "medium", "high"]},
            "period": {"type": "string"}
        },
        "required": ["period"]
    }
}
```

### 3.3 レポートツール

#### 3.3.1 generate_monthly_report

```python
{
    "name": "generate_monthly_report",
    "description": "月次レポート生成",
    "inputSchema": {
        "type": "object",
        "properties": {
            "year": {"type": "integer"},
            "month": {"type": "integer", "minimum": 1, "maximum": 12},
            "format": {"type": "string", "enum": ["summary", "detailed"]}
        },
        "required": ["year", "month"]
    }
}
```

## 4. プロジェクト構造

### 4.1 ディレクトリ構造

```text
my_household_mcpserver/
├── src/
│   ├── household_mcp/
│   │   ├── __init__.py
│   │   ├── server.py          # MCPサーバーのメイン
│   │   ├── database/
│   │   │   ├── __init__.py
│   │   │   ├── models.py      # データモデル定義
│   │   │   ├── connection.py  # DB接続管理
│   │   │   └── migrations.py  # マイグレーション
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── data_tools.py      # データ操作ツール
│   │   │   ├── analysis_tools.py  # 分析ツール
│   │   │   └── report_tools.py    # レポートツール
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── statistics.py  # 統計分析
│   │   │   ├── trends.py      # トレンド分析
│   │   │   └── anomalies.py   # 異常検知
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── formatters.py  # データフォーマット
│   │       └── validators.py  # バリデーション
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── docs/
│   ├── api.md
│   └── usage.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── README.md
└── setup.py
```

```json
### 4.2 設定ファイル

#### 4.2.1 pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "household-mcp-server"
version = "0.1.0"
description = "MCP Server for household budget analysis"
authors = [{name = "Project Team", email = "team@example.com"}]
license = {text = "MIT"}
readme = "README.md"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.104.1",
    "uvicorn>=0.24.0",
    "pandas>=2.1.3",
    "numpy>=1.25.2",
    "matplotlib>=3.8.2",
    "plotly>=5.17.0",
    "pydantic>=2.5.0",
    "python-dateutil>=2.8.2",
    "sqlite3-python",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.3",
    "pytest-asyncio>=0.21.1",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
]

[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3
line_length = 88

[tool.mypy]
python_version = "3.11"
strict = true
```

## 5. データフロー設計

### 5.1 基本的なデータフロー

```text
1. AIエージェント → MCPサーバー (自然言語クエリ)
2. MCPサーバー → クエリ解析 (意図理解)
3. クエリ解析 → データベース (SQLクエリ実行)
4. データベース → 分析エンジン (生データ)
5. 分析エンジン → レスポンス生成 (分析結果)
6. レスポンス生成 → AIエージェント (構造化レスポンス)
```

### 5.2 エラーハンドリング設計

```python
class HouseholdMCPError(Exception):
    """Base exception for household MCP server"""
    pass

class ValidationError(HouseholdMCPError):
    """Data validation error"""
    pass

class DatabaseError(HouseholdMCPError):
    """Database operation error"""
    pass

class AnalysisError(HouseholdMCP):
    """Analysis computation error"""
    pass
```

## 6. セキュリティ設計

### 6.1 データ暗号化

- データベースファイルの暗号化（SQLCipher使用）
- 機密情報のハッシュ化
- 通信の暗号化（TLS）

### 6.2 アクセス制御

```python
# 認証機能
class AuthService:
    def authenticate(self, credentials: dict) -> bool
    def authorize(self, user: User, operation: str) -> bool
    def create_session(self, user: User) -> Session
```

### 6.3 ログ設計

```python
# ログ設定
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': 'household_mcp.log',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'file'],
            'level': 'DEBUG',
            'propagate': False
        }
    }
}
```

## 7. パフォーマンス設計

### 7.1 データベース最適化

- 適切なインデックス設計
- クエリの最適化
- 接続プーリング

### 7.2 キャッシュ戦略

```python
# キャッシュレイヤー
class CacheService:
    def get(self, key: str) -> Optional[Any]
    def set(self, key: str, value: Any, ttl: int = 3600) -> None
    def delete(self, key: str) -> None
```

### 7.3 非同期処理

```python
# 非同期処理での実装
import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時の処理
    await initialize_database()
    yield
    # 終了時の処理
    await cleanup_database()

app = FastAPI(lifespan=lifespan)
```

## 8. テスト設計

### 8.1 テスト戦略

- **Unit Tests**: 各コンポーネントの単体テスト
- **Integration Tests**: コンポーネント間の統合テスト
- **End-to-End Tests**: 全体フローのテスト
- **Performance Tests**: 性能テスト

### 8.2 テストデータ設計

```python
# テストフィクスチャ
@pytest.fixture
def sample_transactions():
    return [
        {
            "date": "2025-07-01",
            "amount": 5000,
            "description": "食費",
            "category": "食費",
            "type": "expense"
        },
        # ... more test data
    ]
```

---

**作成日**: 2025年7月29日  
**バージョン**: 1.0  
**技術責任者**: 開発チーム
