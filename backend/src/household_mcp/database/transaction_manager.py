"""
トランザクション管理とリトライ機構。

SQLAlchemy Session管理、ロールバック、リトライ機能を提供します。
"""

import logging
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator, TypeVar

from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from household_mcp.database.manager import DatabaseManager
from household_mcp.exceptions import HouseholdMCPError

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TransactionError(HouseholdMCPError):
    """トランザクション処理エラー。"""

    pass


class RetryConfig:
    """
    リトライ設定。

    Attributes:
        max_retries: 最大リトライ回数
        backoff_ms: 最初の待機時間（ミリ秒）
        backoff_multiplier: 待機時間の乗数

    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_ms: int = 100,
        backoff_multiplier: float = 1.0,
    ):
        """Initialize RetryConfig."""
        self.max_retries = max_retries
        self.backoff_ms = backoff_ms
        self.backoff_multiplier = backoff_multiplier

    def get_wait_ms(self, retry_count: int) -> int:
        """
        リトライ回数に基づいて待機時間を計算。

        Args:
            retry_count: リトライ回数（0-indexed）

        Returns:
            待機時間（ミリ秒）

        """
        return int(self.backoff_ms * (self.backoff_multiplier**retry_count))


class TransactionManager:
    """
    トランザクション管理。

    Session のライフサイクル管理、自動ロールバック、リトライを提供します。
    """

    def __init__(self, db_manager: DatabaseManager | None = None):
        """
        Initialize TransactionManager.

        Args:
            db_manager: DatabaseManager インスタンス

        """
        self._db_manager = db_manager or DatabaseManager()
        self._retry_config = RetryConfig()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Session スコープコンテキストマネージャ。

        使用例:
            with tm.session_scope() as session:
                session.add(obj)
                session.commit()

        Yields:
            Session: SQLAlchemy Session

        Raises:
            TransactionError: コミット失敗時

        """
        session = self._db_manager.get_session()
        try:
            yield session
            session.commit()
            logger.debug("トランザクションをコミットしました")
        except IntegrityError as e:
            session.rollback()
            logger.error(f"整合性エラーが発生しました: {e}")
            raise TransactionError(f"整合性エラーが発生しました: {e}") from e
        except OperationalError as e:
            session.rollback()
            logger.error(f"DB操作エラーが発生しました: {e}")
            raise TransactionError(f"DB操作エラーが発生しました: {e}") from e
        except Exception as e:
            session.rollback()
            logger.error(f"予期しないエラーが発生しました: {e}")
            raise TransactionError(f"予期しないエラーが発生しました: {e}") from e
        finally:
            session.close()

    @contextmanager
    def session_scope_nested(self, session: Session) -> Generator[Session, None, None]:
        """
        ネストされた Session スコープ（既存 Session を使用）。

        使用例:
            with tm.session_scope() as outer_session:
                with tm.session_scope_nested(outer_session) as inner_session:
                    inner_session.add(obj)

        Args:
            session: 既存の SQLAlchemy Session

        Yields:
            Session: 渡された Session

        """
        try:
            yield session
        except IntegrityError as e:
            logger.error(f"ネストされたトランザクション整合性エラー: {e}")
            raise TransactionError(
                f"ネストされたトランザクション整合性エラー: {e}"
            ) from e
        except Exception as e:
            logger.error(f"ネストされたトランザクションエラー: {e}")
            raise TransactionError(f"ネストされたトランザクションエラー: {e}") from e

    def execute_with_retry(
        self,
        func: Callable[..., T],
        *args: Any,
        retry_config: RetryConfig | None = None,
        **kwargs: Any,
    ) -> T:
        """
        リトライ機構付きで関数を実行。

        IntegrityError と OperationalError に対してリトライを試みます。

        使用例:
            def add_transaction(session):
                tx = Transaction(...)
                session.add(tx)
                session.commit()
                return tx

            result = tm.execute_with_retry(
                add_transaction,
                session
            )

        Args:
            func: 実行関数
            *args: 位置引数
            retry_config: リトライ設定（デフォルト: 3回、100ms間隔）
            **kwargs: キーワード引数

        Returns:
            関数の戻り値

        Raises:
            TransactionError: 全リトライ失敗時

        """
        config = retry_config or self._retry_config
        last_error: Exception | None = None

        for attempt in range(config.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 0:
                    logger.info(
                        f"リトライ {attempt} 回目で成功しました: {func.__name__}"
                    )
                return result
            except (IntegrityError, OperationalError) as e:
                last_error = e
                if attempt < config.max_retries:
                    wait_ms = config.get_wait_ms(attempt)
                    logger.warning(
                        f"リトライ対象エラーが発生しました "
                        f"({attempt + 1}/{config.max_retries}): {e} "
                        f"({wait_ms}ms 後に再試行)"
                    )
                    time.sleep(wait_ms / 1000.0)
                else:
                    logger.error(
                        f"全リトライが失敗しました ({config.max_retries + 1}回): {e}"
                    )
        raise TransactionError(
            f"トランザクション実行失敗: {last_error}"
        ) from last_error

    def execute_in_transaction(
        self,
        func: Callable[[Session], T],
        retry_config: RetryConfig | None = None,
    ) -> T:
        """
        トランザクション内で関数を実行（リトライ付き）。

        使用例:
            def add_transaction(session):
                tx = Transaction(...)
                session.add(tx)
                return tx

            result = tm.execute_in_transaction(add_transaction)

        Args:
            func: Session を受け取る関数
            retry_config: リトライ設定

        Returns:
            関数の戻り値

        Raises:
            TransactionError: 実行失敗時

        """

        def wrapper() -> T:
            with self.session_scope() as session:
                return func(session)

        return self.execute_with_retry(wrapper, retry_config=retry_config)

    def rollback_and_close(self, session: Session) -> None:
        """
        Session をロールバックしてクローズ。

        Args:
            session: ロールバックする Session

        """
        try:
            session.rollback()
            logger.debug("トランザクションをロールバックしました")
        except Exception as e:
            logger.error(f"ロールバック中にエラーが発生しました: {e}")
        finally:
            session.close()


# グローバル TransactionManager インスタンス
_transaction_manager: TransactionManager | None = None


def get_transaction_manager() -> TransactionManager:
    """
    グローバル TransactionManager インスタンスを取得。

    遅延初期化を使用します。

    Returns:
        TransactionManager インスタンス

    """
    global _transaction_manager
    if _transaction_manager is None:
        _transaction_manager = TransactionManager()
    return _transaction_manager
