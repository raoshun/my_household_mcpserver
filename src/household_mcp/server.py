"""家計簿分析MCPサーバーのメインサーバー実装.

FastAPIベースのWebAPIサーバーアプリケーション
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database.connection import close_database_connection, get_database_connection
from .database.migrations import create_migration_manager
from .tools.data_tools import (
    get_account_manager,
    get_category_manager,
    get_transaction_manager,
)

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理."""
    # 起動時処理
    logger.info("Starting Household MCP Server...")

    try:
        # データベース接続とマイグレーション
        migration_manager = create_migration_manager()
        migration_status = migration_manager.get_migration_status()

        if migration_status["pending_count"] > 0:
            logger.info(
                "Applying %d pending migrations...", migration_status["pending_count"]
            )
            success = migration_manager.migrate_up()
            if success:
                logger.info("All migrations applied successfully")
            else:
                logger.error("Failed to apply some migrations")
        else:
            logger.info("Database is up to date")

        # サーバー起動完了
        logger.info("Household MCP Server started successfully")
        yield

    except Exception as e:
        logger.error("Failed to start server: %s", e)
        raise

    finally:
        # シャットダウン時処理
        logger.info("Shutting down Household MCP Server...")
        close_database_connection()
        logger.info("Household MCP Server stopped")


# FastAPIアプリケーション作成
app = FastAPI(
    title="Household MCP Server",
    description="家計簿データ管理・分析用MCPサーバー",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限する
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== エラーハンドリング =====


class HouseholdMCPError(Exception):
    """家計簿MCPサーバー用カスタム例外基底クラス."""

    def __init__(self, message: str, error_code: str = "GENERAL_ERROR"):
        """初期化.

        Args:
            message: エラーメッセージ
            error_code: エラーコード
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class DatabaseError(HouseholdMCPError):
    """データベース関連エラー."""

    def __init__(self, message: str):
        """初期化.

        Args:
            message: エラーメッセージ
        """
        super().__init__(message, "DATABASE_ERROR")


class ValidationError(HouseholdMCPError):
    """データ検証エラー."""

    def __init__(self, message: str):
        """初期化.

        Args:
            message: エラーメッセージ
        """
        super().__init__(message, "VALIDATION_ERROR")


class NotFoundError(HouseholdMCPError):
    """リソース未発見エラー."""

    def __init__(self, message: str):
        """初期化.

        Args:
            message: エラーメッセージ
        """
        super().__init__(message, "NOT_FOUND_ERROR")


@app.exception_handler(HouseholdMCPError)
async def household_error_handler(request: Request, exc: HouseholdMCPError):
    """カスタム例外ハンドラー."""
    logger.error("Household MCP Error: %s [%s]", exc.message, exc.error_code)
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "type": "HouseholdMCPError",
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """一般例外ハンドラー."""
    logger.error("Unexpected error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "type": "InternalServerError",
            }
        },
    )


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント."""
    try:
        # データベース接続チェック
        db_connection = get_database_connection()
        db_status = (
            "healthy"
            if db_connection.table_exists("schema_migrations")
            else "unhealthy"
        )

        # マイグレーション状態チェック
        migration_manager = create_migration_manager()
        migration_status = migration_manager.get_migration_status()

        return {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",  # 実際の実装では datetime.utcnow()
            "version": "0.1.0",
            "database": {
                "status": db_status,
                "current_version": migration_status.get("current_version"),
                "pending_migrations": migration_status.get("pending_count", 0),
            },
            "server": {"name": "household-mcp", "type": "FastAPI"},
        }

    except Exception as e:
        logger.error("Health check failed: %s", e)
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/")
async def root():
    """ルートエンドポイント."""
    return {
        "message": "Household MCP Server",
        "version": "0.1.0",
        "description": "家計簿データ管理・分析用MCPサーバー",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "database_status": "/api/database/status",
        },
    }


@app.get("/api/tools")
async def list_available_tools():
    """利用可能なツールのリストを返す."""
    return {
        "tools": [
            {
                "name": "get_server_info",
                "description": "サーバー情報と利用可能な機能の概要を取得",
                "parameters": {},
            },
            {
                "name": "get_database_status",
                "description": "データベースの状態とマイグレーション情報を取得",
                "parameters": {},
            },
        ]
    }


@app.get("/api/server/info")
async def get_server_info():
    """サーバー情報を取得."""
    info = {
        "server_name": "Household MCP Server",
        "version": "0.1.0",
        "description": "家計簿データの管理・分析機能を提供するMCPサーバー",
        "features": [
            "取引データ管理 (CRUD操作)",
            "カテゴリー・アカウント管理",
            "データ分析・統計機能",
            "予算管理",
            "レポート生成",
        ],
        "database": "SQLite",
        "supported_currencies": ["JPY", "USD", "EUR"],
    }

    return info


@app.get("/api/database/status")
async def get_database_status():
    """データベース状態を取得."""
    try:
        migration_manager = create_migration_manager()
        status = migration_manager.get_migration_status()

        db_connection = get_database_connection()
        table_names = db_connection.get_table_names()

        # 各テーブルの行数を取得
        table_counts = {}
        for table in ["transactions", "categories", "accounts", "budgets"]:
            if table in table_names:
                table_counts[table] = db_connection.get_row_count(table)

        return {
            "connection_status": "healthy",
            "current_version": status.get("current_version"),
            "latest_version": status.get("latest_version"),
            "applied_migrations": status.get("applied_count", 0),
            "pending_migrations": status.get("pending_count", 0),
            "tables": table_counts,
        }

    except Exception as e:
        logger.error("Failed to get database status: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Database status check failed: {str(e)}"
        )


# ===== 取引管理API =====


@app.post("/api/transactions")
async def add_transaction(transaction_data: dict):
    """新しい取引を追加."""
    transaction_manager = get_transaction_manager()

    required_fields = [
        "date",
        "amount",
        "description",
        "category_name",
        "account_name",
        "type",
    ]
    for field in required_fields:
        if field not in transaction_data:
            raise HTTPException(
                status_code=400, detail=f"Missing required field: {field}"
            )

    result = transaction_manager.add_transaction(
        date=transaction_data["date"],
        amount=transaction_data["amount"],
        description=transaction_data["description"],
        category_name=transaction_data["category_name"],
        account_name=transaction_data["account_name"],
        type=transaction_data["type"],
    )

    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["message"])


@app.get("/api/transactions")
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category_name: Optional[str] = None,
    account_name: Optional[str] = None,
    transaction_type: Optional[str] = None,
):
    """取引一覧を取得."""
    transaction_manager = get_transaction_manager()

    result = transaction_manager.get_transactions(
        limit=limit,
        offset=offset,
        start_date=start_date,
        end_date=end_date,
        category_name=category_name,
        account_name=account_name,
        transaction_type=transaction_type,
    )

    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result["message"])


@app.put("/api/transactions/{transaction_id}")
async def update_transaction(transaction_id: int, update_data: dict):
    """取引を更新."""
    transaction_manager = get_transaction_manager()

    result = transaction_manager.update_transaction(transaction_id, **update_data)

    if result["success"]:
        return result
    else:
        status_code = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status_code, detail=result["message"])


@app.delete("/api/transactions/{transaction_id}")
async def delete_transaction(transaction_id: int):
    """取引を削除."""
    transaction_manager = get_transaction_manager()

    result = transaction_manager.delete_transaction(transaction_id)

    if result["success"]:
        return result
    else:
        status_code = 404 if "not found" in result.get("error", "").lower() else 400
        raise HTTPException(status_code=status_code, detail=result["message"])


# ===== カテゴリー管理API =====


@app.get("/api/categories")
async def get_categories(category_type: Optional[str] = None):
    """カテゴリー一覧を取得."""
    category_manager = get_category_manager()

    if category_type and category_type not in ["income", "expense"]:
        raise HTTPException(
            status_code=400, detail="category_type must be 'income' or 'expense'"
        )

    result = category_manager.get_categories(category_type=category_type)

    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=500, detail=result["message"])


@app.post("/api/categories")
async def add_category(category_data: dict):
    """新しいカテゴリーを追加."""
    category_manager = get_category_manager()

    required_fields = ["name", "type"]
    for field in required_fields:
        if field not in category_data:
            raise HTTPException(
                status_code=400, detail=f"Missing required field: {field}"
            )

    result = category_manager.add_category(
        name=category_data["name"],
        category_type=category_data["type"],
        parent_id=category_data.get("parent_id"),
        color=category_data.get("color"),
        icon=category_data.get("icon"),
    )

    if result["success"]:
        return result
    else:
        status_code = 409 if "DUPLICATE" in result.get("error", "") else 400
        raise HTTPException(status_code=status_code, detail=result["message"])


@app.put("/api/categories/{category_id}")
async def update_category(category_id: int, update_data: dict):
    """カテゴリーを更新."""
    category_manager = get_category_manager()

    result = category_manager.update_category(category_id, **update_data)

    if result["success"]:
        return result
    else:
        status_code = 404 if "NOT_FOUND" in result.get("error", "") else 400
        raise HTTPException(status_code=status_code, detail=result["message"])


@app.delete("/api/categories/{category_id}")
async def delete_category(category_id: int):
    """カテゴリーを削除."""
    category_manager = get_category_manager()

    result = category_manager.delete_category(category_id)

    if result["success"]:
        return result
    else:
        if "NOT_FOUND" in result.get("error", ""):
            status_code = 404
        elif "IN_USE" in result.get("error", "") or "HAS_CHILDREN" in result.get(
            "error", ""
        ):
            status_code = 409
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=result["message"])


# ===== アカウント管理 API =====


@app.get("/api/accounts")
async def get_accounts(
    account_type: Optional[str] = None, is_active: Optional[bool] = None
):
    """アカウント一覧を取得."""
    account_manager = get_account_manager()

    accounts = account_manager.get_accounts(
        account_type=account_type, is_active=is_active
    )

    return {"accounts": accounts, "count": len(accounts)}


@app.post("/api/accounts")
async def create_account(account_data: dict):
    """新しいアカウントを作成."""
    account_manager = get_account_manager()

    # 必須パラメーターの確認
    if not account_data.get("name"):
        raise HTTPException(status_code=400, detail="アカウント名は必須です")

    if not account_data.get("type"):
        raise HTTPException(status_code=400, detail="アカウント種別は必須です")

    result = account_manager.add_account(
        name=str(account_data["name"]),
        account_type=str(account_data["type"]),
        initial_balance=float(account_data.get("initial_balance", 0.0)),
        is_active=bool(account_data.get("is_active", True)),
    )

    if result["success"]:
        return result
    else:
        status_code = 400
        if "DUPLICATE_NAME" in result.get("error", ""):
            status_code = 409
        raise HTTPException(status_code=status_code, detail=result["message"])


@app.get("/api/accounts/{account_id}")
async def get_account(account_id: int):
    """指定IDのアカウントを取得."""
    account_manager = get_account_manager()

    account = account_manager.get_account(account_id)

    if account:
        return account
    else:
        raise HTTPException(
            status_code=404, detail=f"アカウントID {account_id} が見つかりません"
        )


@app.put("/api/accounts/{account_id}")
async def update_account(account_id: int, account_data: dict):
    """アカウント情報を更新."""
    account_manager = get_account_manager()

    result = account_manager.update_account(
        account_id=account_id,
        name=account_data.get("name"),
        account_type=account_data.get("type"),
        is_active=account_data.get("is_active"),
    )

    if result["success"]:
        return result
    else:
        status_code = 404 if "NOT_FOUND" in result.get("error", "") else 400
        if "DUPLICATE_NAME" in result.get("error", ""):
            status_code = 409
        raise HTTPException(status_code=status_code, detail=result["message"])


@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: int):
    """アカウントを削除."""
    account_manager = get_account_manager()

    result = account_manager.delete_account(account_id)

    if result["success"]:
        return result
    else:
        if "NOT_FOUND" in result.get("error", ""):
            status_code = 404
        elif "IN_USE" in result.get("error", ""):
            status_code = 409
        else:
            status_code = 400
        raise HTTPException(status_code=status_code, detail=result["message"])


@app.put("/api/accounts/{account_id}/balance")
async def update_account_balance(account_id: int, balance_data: dict):
    """アカウント残高を更新."""
    account_manager = get_account_manager()

    # 必須パラメーターの確認
    if "balance" not in balance_data:
        raise HTTPException(status_code=400, detail="残高は必須です")

    try:
        new_balance = float(balance_data["balance"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="残高は数値である必要があります")

    result = account_manager.update_balance(
        account_id=account_id, new_balance=new_balance
    )

    if result["success"]:
        return result
    else:
        status_code = 404 if "NOT_FOUND" in result.get("error", "") else 400
        raise HTTPException(status_code=status_code, detail=result["message"])


# ===== サーバー起動関数 =====


def start_server(host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
    """サーバーを起動."""
    uvicorn.run(
        "household_mcp.server:app",
        host=host,
        port=port,
        reload=debug,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"level": "INFO", "handlers": ["default"]},
        },
    )


if __name__ == "__main__":
    start_server(debug=True)
