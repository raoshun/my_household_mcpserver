"""Database manager for household MCP server."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


@event.listens_for(Engine, "connect")  # type: ignore[misc]
def set_sqlite_pragma(dbapi_conn: Any, _connection_record: Any) -> None:
    """SQLite接続時にプラグマを設定."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    # テストやローカル実行の高速化用チューニング（安全性より速度優先）
    # 有効化条件: 環境変数 HOUSEHOLD_SQLITE_FAST=1（デフォルト有効）
    fast = os.getenv("HOUSEHOLD_SQLITE_FAST", "1") == "1"
    if fast:
        try:
            cursor.execute("PRAGMA journal_mode=MEMORY")
        except Exception:
            # 一部環境で失敗しても致命的ではない
            pass
        cursor.execute("PRAGMA synchronous=OFF")
        cursor.execute("PRAGMA temp_store=MEMORY")
        # 負の値はKB単位のページを示しメモリキャッシュ拡張
        cursor.execute("PRAGMA cache_size=-64000")
    cursor.close()


class DatabaseManager:
    """データベース管理クラス."""

    def __init__(self, db_path: str = "data/household.db"):
        """初期化.

        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None

    @property
    def engine(self) -> Engine:
        """SQLAlchemyエンジンを取得."""
        if self._engine is None:
            # ディレクトリが存在しない場合は作成
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            # エンジン作成
            self._engine = create_engine(
                f"sqlite:///{self.db_path}",
                echo=False,  # SQLログを出力しない
                future=True,  # SQLAlchemy 2.0スタイル
            )
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """セッションファクトリを取得."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                expire_on_commit=False,
            )
        return self._session_factory

    def initialize_database(self) -> None:
        """データベースを初期化（テーブル作成）."""
        Base.metadata.create_all(self.engine)

    def drop_all_tables(self) -> None:
        """すべてのテーブルを削除（テスト用）."""
        Base.metadata.drop_all(self.engine)

    def database_exists(self) -> bool:
        """データベースファイルが存在するか確認."""
        return os.path.exists(self.db_path)

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """トランザクション付きセッションのコンテキストマネージャ.

        Yields:
            Session: データベースセッション

        Example:
            with db_manager.session_scope() as session:
                transaction = Transaction(...)
                session.add(transaction)
                # コミットは自動的に行われる
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_session(self) -> Session:
        """新しいセッションを取得（手動管理用）.

        Returns:
            Session: データベースセッション

        Note:
            このメソッドで取得したセッションは、
            呼び出し側で明示的にclose()する必要があります。
            通常はsession_scope()の使用を推奨します。
        """
        return self.session_factory()

    def close(self) -> None:
        """エンジンとすべての接続をクローズ.

        テスト終了時やアプリケーション終了時に明示的に呼び出すことで、
        ResourceWarning を回避できます。
        """
        if self._engine is not None:
            # 全コネクションプールを破棄（接続クローズを確実に）
            self._engine.dispose()
            self._engine = None
            self._session_factory = None
