"""Services and data structures for FIRE asset snapshots."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import date, datetime
from datetime import time as dt_time
from typing import Any, Callable, Protocol, Sequence, TypeVar, cast

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from household_mcp.analysis.financial_independence import FinancialIndependenceAnalyzer
from household_mcp.analysis.fire_calculator import FIRECalculator
from household_mcp.database.manager import DatabaseManager
from household_mcp.database.models import FIProgressCache, FireAssetSnapshot
from household_mcp.dataloader import HouseholdDataLoader

SNAPSHOT_CATEGORIES: tuple[str, ...] = (
    "cash_and_deposits",
    "stocks_cash",
    "stocks_margin",
    "investment_trusts",
    "pension",
    "points",
)


class FireSnapshotRequest(BaseModel):
    """Input payload for registering or validating a FIRE snapshot."""

    snapshot_date: date = Field(..., description="スナップショット日")
    cash_and_deposits: int = Field(0, ge=0, description="現金・預金")
    stocks_cash: int = Field(0, ge=0, description="株式（現物）")
    stocks_margin: int = Field(0, ge=0, description="株式（信用）")
    investment_trusts: int = Field(0, ge=0, description="投資信託")
    pension: int = Field(0, ge=0, description="年金")
    points: int = Field(0, ge=0, description="ポイント・マイル")
    notes: str | None = Field(None, max_length=2000, description="備考")

    model_config = ConfigDict(extra="forbid")

    def category_totals(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in SNAPSHOT_CATEGORIES}


class FireSnapshotResponse(FireSnapshotRequest):
    """API/MCP応答に利用するスナップショット情報."""

    total: int = Field(..., ge=0, description="カテゴリ合計")
    is_interpolated: bool = Field(False, description="補完値かどうか")


@dataclass(frozen=True)
class SnapshotPoint:
    """補完向けのスナップショット値."""

    snapshot_date: date
    values: dict[str, int]


class SnapshotInterpolator(Protocol):
    """スナップショット補完インターフェース."""

    def interpolate(
        self,
        target_date: date,
        ordered_snapshots: Sequence[SnapshotPoint],
    ) -> dict[str, int]:
        """補完結果のカテゴリ値を返す."""


class LinearSnapshotInterpolator(SnapshotInterpolator):
    """最小限の線形補完実装."""

    def __init__(
        self,
        categories: Sequence[str] = SNAPSHOT_CATEGORIES,
    ) -> None:
        self._categories = tuple(categories)

    def interpolate(
        self,
        target_date: date,
        ordered_snapshots: Sequence[SnapshotPoint],
    ) -> dict[str, int]:
        if not ordered_snapshots:
            msg = "at least one snapshot is required for interpolation"
            raise ValueError(msg)

        # 1. Exact match
        for point in ordered_snapshots:
            if point.snapshot_date == target_date:
                return dict(point.values)

        previous: SnapshotPoint | None = None
        following: SnapshotPoint | None = None

        for point in ordered_snapshots:
            if point.snapshot_date < target_date:
                previous = point
            elif point.snapshot_date > target_date:
                following = point
                break

        if previous and following:
            span_days = (following.snapshot_date - previous.snapshot_date).days
            if span_days <= 0:
                return dict(previous.values)
            offset_days = (target_date - previous.snapshot_date).days
            ratio = offset_days / span_days
            blended: dict[str, int] = {}
            for name in self._categories:
                start = previous.values.get(name, 0)
                end = following.values.get(name, 0)
                value = start + (end - start) * ratio
                blended[name] = round(value)
            return blended

        if previous:
            return dict(previous.values)
        if following:
            return dict(following.values)

        return dict(ordered_snapshots[0].values)


logger = logging.getLogger(__name__)
T = TypeVar("T")


class SnapshotNotFoundError(RuntimeError):
    """Raised when no snapshot exists for the requested date."""


class FireSnapshotService:
    """Handle FIRE snapshot registration, interpolation, and cache updates."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        *,
        interpolator: SnapshotInterpolator | None = None,
        analyzer: FinancialIndependenceAnalyzer | None = None,
        data_loader: HouseholdDataLoader | None = None,
        history_window: int = 12,
        default_annual_expense: float = 1_200_000.0,
        withdrawal_rate: float = 0.04,
        retry_attempts: int = 3,
        retry_interval_sec: float = 0.1,
    ) -> None:
        self.db_manager = db_manager
        self.interpolator = interpolator or LinearSnapshotInterpolator()
        self.analyzer = analyzer or FinancialIndependenceAnalyzer()
        self.data_loader = data_loader
        self.history_window = history_window
        self.default_annual_expense = default_annual_expense
        self.withdrawal_rate = withdrawal_rate
        self.retry_attempts = retry_attempts
        self.retry_interval_sec = retry_interval_sec
        # Ensure the database schema exists for services which run without
        # an explicit DatabaseManager.initialize_database() call in tests or
        # higher-level app setup. This is idempotent and safe for production
        # where the database is already initialized.
        try:
            self.db_manager.initialize_database()
        except Exception:
            # Avoid failing service initialization for environments where the
            # DB is intentionally absent (e.g., limited unit tests).
            logger.debug(
                "Database initialization skipped in FireSnapshotService.__init__"
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def recalculate_fi_cache(self, snapshot_date: date | None = None) -> None:
        """
        Recalculate FI cache for the specified or latest snapshot.

        This is a public wrapper that manages the DB session and resolves the
        target snapshot date, then delegates to the internal implementation
        that performs the actual cache update.
        """

        def _operation() -> None:
            with self.db_manager.session_scope() as session:
                target_date = self._resolve_snapshot_date(
                    session,
                    snapshot_date,
                )
                if target_date is None:
                    raise SnapshotNotFoundError(
                        "No snapshots available for recalculation"
                    )
                self._recalculate_fi_cache(session, target_date)

        self._run_with_retry(_operation)

    def register_snapshot(
        self,
        request: FireSnapshotRequest,
    ) -> FireSnapshotResponse:
        """Persist a snapshot and refresh FI cache."""

        def _operation() -> FireSnapshotResponse:
            with self.db_manager.session_scope() as session:
                target_date = request.snapshot_date
                snapshot = (
                    session.query(FireAssetSnapshot)
                    .filter(FireAssetSnapshot.snapshot_date == target_date)
                    .one_or_none()
                )
                if snapshot is None:
                    snapshot = FireAssetSnapshot(snapshot_date=target_date)
                    session.add(snapshot)

                for field, value in request.category_totals().items():
                    setattr(snapshot, field, value)
                snapshot.notes = request.notes
                snapshot.updated_at = datetime.utcnow()

                session.flush()
                self._recalculate_fi_cache(session, target_date)

                categories = request.category_totals()
                return self._build_response(
                    snapshot_date=target_date,
                    categories=categories,
                    is_interpolated=False,
                    notes=request.notes,
                )

        return self._run_with_retry(_operation)

    def get_snapshot(
        self,
        snapshot_date: date | None = None,
        *,
        allow_interpolation: bool = True,
    ) -> FireSnapshotResponse:
        """Return a snapshot for the date, interpolating when necessary."""

        def _operation() -> FireSnapshotResponse:
            with self.db_manager.session_scope() as session:
                target_date = snapshot_date or self._get_latest_snapshot_date(session)
                if target_date is None:
                    raise SnapshotNotFoundError("No snapshots available yet")

                return self._snapshot_from_session(
                    session,
                    target_date,
                    allow_interpolation=allow_interpolation,
                )

        return self._run_with_retry(_operation)

    def get_status(
        self,
        snapshot_date: date | None = None,
        *,
        months: int = 12,
    ) -> dict[str, Any]:
        """Return FI status along with snapshot and history metadata."""

        def _operation() -> dict[str, Any]:
            with self.db_manager.session_scope() as session:
                target_date = snapshot_date or self._get_latest_snapshot_date(session)
                if target_date is None:
                    raise SnapshotNotFoundError("No snapshots available")

                cache_entry = self._ensure_cache_entry(session, target_date)
                snapshot_resp = self._snapshot_from_session(
                    session,
                    target_date,
                    allow_interpolation=True,
                )
                history = self._history_payload(session, target_date, months)

                return {
                    "snapshot": snapshot_resp.model_dump(),
                    "fi_progress": self._cache_payload(cache_entry),
                    "history": history,
                }

        return self._run_with_retry(_operation)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _run_with_retry(self, func: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return func()
            except OperationalError as exc:  # pragma: no cover - depends on db
                locked = "database is locked" in str(exc).lower()
                if locked and attempt < self.retry_attempts:
                    last_error = exc
                    logger.warning(
                        "SQLite database is locked (attempt %s/%s)",
                        attempt,
                        self.retry_attempts,
                    )
                    time.sleep(self.retry_interval_sec)
                    continue
                raise
        if last_error is not None:  # pragma: no cover - defensive
            raise last_error
        raise RuntimeError("Retry logic exited unexpectedly")  # pragma: no cover

    def _extract_values(self, snapshot: FireAssetSnapshot) -> dict[str, int]:
        return {name: getattr(snapshot, name, 0) for name in SNAPSHOT_CATEGORIES}

    def _sum_categories(self, values: dict[str, int]) -> int:
        return int(sum(values.values()))

    def _build_response(
        self,
        *,
        snapshot_date: date,
        categories: dict[str, int],
        is_interpolated: bool,
        notes: str | None,
    ) -> FireSnapshotResponse:
        payload = {
            **categories,
            "snapshot_date": snapshot_date,
            "notes": notes,
            "total": self._sum_categories(categories),
            "is_interpolated": is_interpolated,
        }
        return FireSnapshotResponse.model_validate(payload)

    def _load_snapshot_points(
        self,
        session: Session,
        *,
        up_to: date | None = None,
    ) -> list[SnapshotPoint]:
        query = session.query(FireAssetSnapshot).order_by(
            FireAssetSnapshot.snapshot_date.asc()
        )
        if up_to is not None:
            query = query.filter(FireAssetSnapshot.snapshot_date <= up_to)
        snapshots = query.all()
        return [
            SnapshotPoint(
                cast(date, snapshot.snapshot_date),
                self._extract_values(snapshot),
            )
            for snapshot in snapshots
        ]

    def _history_payload(
        self,
        session: Session,
        target_date: date,
        months: int,
    ) -> list[dict[str, Any]]:
        points = self._load_snapshot_points(session, up_to=target_date)
        if not points:
            return []
        start_idx = max(len(points) - months, 0)
        trimmed = points[start_idx:]
        return [
            {
                "snapshot_date": point.snapshot_date.isoformat(),
                "total": self._sum_categories(point.values),
            }
            for point in trimmed
        ]

    def _get_latest_snapshot_date(self, session: Session) -> date | None:
        result = (
            session.query(FireAssetSnapshot.snapshot_date)
            .order_by(FireAssetSnapshot.snapshot_date.desc())
            .first()
        )
        return result[0] if result else None

    def _resolve_snapshot_date(
        self, session: Session, snapshot_date: date | None
    ) -> date | None:
        if snapshot_date is not None:
            return snapshot_date
        return self._get_latest_snapshot_date(session)

    def _snapshot_from_session(
        self,
        session: Session,
        target_date: date,
        *,
        allow_interpolation: bool,
    ) -> FireSnapshotResponse:
        snapshot = (
            session.query(FireAssetSnapshot)
            .filter(FireAssetSnapshot.snapshot_date == target_date)
            .one_or_none()
        )
        if snapshot is not None:
            values = self._extract_values(snapshot)
            notes = cast(str | None, getattr(snapshot, "notes", None))
            return self._build_response(
                snapshot_date=target_date,
                categories=values,
                is_interpolated=False,
                notes=notes,
            )

        if not allow_interpolation:
            raise SnapshotNotFoundError(f"No snapshot for {target_date}")

        points = self._load_snapshot_points(session)
        interpolated = self.interpolator.interpolate(target_date, points)
        return self._build_response(
            snapshot_date=target_date,
            categories=interpolated,
            is_interpolated=True,
            notes=None,
        )

    def _ensure_cache_entry(
        self, session: Session, snapshot_date: date
    ) -> FIProgressCache:
        snapshot_dt = self._to_datetime(snapshot_date)
        cache = (
            session.query(FIProgressCache)
            .filter(FIProgressCache.snapshot_date == snapshot_dt)
            .one_or_none()
        )
        if cache:
            return cache
        return self._recalculate_fi_cache(session, snapshot_date)

    def _to_datetime(self, value: date) -> datetime:
        return datetime.combine(value, dt_time.min)

    def _recalculate_fi_cache(
        self,
        session: Session,
        snapshot_date: date,
    ) -> FIProgressCache:
        all_points = self._load_snapshot_points(session)
        if not all_points:
            raise SnapshotNotFoundError("No snapshots for cache calculation")

        history_points = [
            point for point in all_points if point.snapshot_date <= snapshot_date
        ]
        if not history_points:
            # target date precedes earliest snapshot → still interpolate
            interpolated = self.interpolator.interpolate(
                snapshot_date,
                all_points,
            )
            history_points = [SnapshotPoint(snapshot_date, interpolated)]
        elif history_points[-1].snapshot_date != snapshot_date:
            interpolated = self.interpolator.interpolate(
                snapshot_date,
                all_points,
            )
            history_points.append(SnapshotPoint(snapshot_date, interpolated))

        start_idx = max(len(history_points) - self.history_window, 0)
        history_points = history_points[start_idx:]
        asset_history = [
            float(self._sum_categories(point.values)) for point in history_points
        ]
        current_total = asset_history[-1]
        annual_expense = self._estimate_annual_expense(
            asset_history, snapshot_date=snapshot_date
        )

        target_assets = FIRECalculator.calculate_fire_target(annual_expense)
        status = self.analyzer.get_status(
            current_assets=current_total,
            target_assets=target_assets,
            annual_expense=annual_expense,
            asset_history=asset_history,
        )

        snapshot_dt = self._to_datetime(snapshot_date)
        cache = (
            session.query(FIProgressCache)
            .filter(FIProgressCache.snapshot_date == snapshot_dt)
            .one_or_none()
        )
        if cache is None:
            cache = FIProgressCache(
                snapshot_date=snapshot_dt,
                data_period_end=snapshot_dt,
                current_assets=current_total,
                annual_expense=annual_expense,
                fire_target=status["fire_target"],
                progress_rate=status["progress_rate"],
            )
            session.add(cache)

        cache_obj = cast(Any, cache)
        cache_obj.data_period_end = snapshot_dt
        cache_obj.current_assets = current_total
        cache_obj.annual_expense = annual_expense
        cache_obj.fire_target = status["fire_target"]
        cache_obj.progress_rate = status["progress_rate"]

        growth = status.get("growth_analysis") or {}
        cache_obj.monthly_growth_rate = growth.get("growth_rate_decimal")
        cache_obj.growth_confidence = growth.get("confidence")
        cache_obj.data_points_used = growth.get("data_points")
        months_to_fi = status.get("months_to_fi")
        cache_obj.months_to_fi = months_to_fi
        cache_obj.is_achievable = 1 if months_to_fi not in (None, -1) else 0
        cache_obj.projected_12m = None
        cache_obj.projected_60m = None
        cache_obj.analysis_method = "linear_interpolation"

        return cache

    def _calculate_annual_expense_from_csv(
        self,
        snapshot_date: date,
    ) -> float | None:
        """
        Calculate annual expense from CSV data with fallback logic.

        Priority:
        1. Use 12-month CSV data if available
        2. Use 6-month data and annualize if 12-month unavailable
        3. Return None if insufficient data (fallback to asset-based)

        Args:
            snapshot_date: Target date for calculation

        Returns:
            Annual expense in JPY, or None if insufficient data

        """
        if self.data_loader is None:
            return None

        try:
            # Get all available months
            available_months = list(self.data_loader.iter_available_months())
            logger.debug(
                "Available months from data_loader: %s",
                available_months,
            )
            if not available_months:
                return None

            # Filter months <= snapshot_date
            target_year = snapshot_date.year
            target_month = snapshot_date.month
            valid_months = [
                (y, m)
                for y, m in available_months
                if (y, m) <= (target_year, target_month)
            ]
            logger.debug(
                "Valid months for snapshot %s: %s",
                snapshot_date,
                valid_months,
            )

            if not valid_months:
                return None

            # Try 12-month calculation
            if len(valid_months) >= 12:
                recent_12 = valid_months[-12:]
                df = self.data_loader.load_many(recent_12)
                total_expense = abs(df["金額（円）"].sum())
                if total_expense > 0:
                    logger.info(
                        "Annual expense calculated from 12-month CSV: ¥%s",
                        f"{total_expense:,.0f}",
                    )
                    return float(total_expense)

            # Try 6-month annualization
            if len(valid_months) >= 6:
                recent_6 = valid_months[-6:]
                df = self.data_loader.load_many(recent_6)
                six_month_expense = abs(df["金額（円）"].sum())
                if six_month_expense > 0:
                    annualized = six_month_expense * 2.0
                    logger.info(
                        "Annual expense annualized from 6-month CSV: ¥%s (6mo: ¥%s)",
                        f"{annualized:,.0f}",
                        f"{six_month_expense:,.0f}",
                    )
                    return float(annualized)

            return None

        except Exception as exc:
            logger.warning(
                "Failed to calculate annual expense from CSV: %s",
                exc,
                exc_info=True,
            )
            return None

    def _estimate_annual_expense(
        self,
        asset_history: Sequence[float],
        snapshot_date: date | None = None,
    ) -> float:
        """
        Estimate annual expense with priority: CSV > asset-based > default.

        Args:
            asset_history: Historical asset values
            snapshot_date: Target date for CSV calculation (optional)

        Returns:
            Estimated annual expense in JPY

        """
        # Priority 1: CSV-based calculation
        if snapshot_date is not None:
            csv_expense = self._calculate_annual_expense_from_csv(snapshot_date)
            if csv_expense is not None:
                return csv_expense

        # Priority 2: Asset-based estimation (4% withdrawal rate)
        if asset_history:
            derived = asset_history[-1] * self.withdrawal_rate
            if derived >= 1.0:
                logger.info(
                    "Annual expense estimated from assets (4%% rule): ¥%s",
                    f"{derived:,.0f}",
                )
                return float(max(derived, 1.0))

        # Priority 3: Default value
        logger.info(
            "Annual expense using default value: ¥%s",
            f"{self.default_annual_expense:,.0f}",
        )
        return float(self.default_annual_expense)

    def _cache_payload(self, cache: FIProgressCache) -> dict[str, Any]:
        cache_obj = cast(Any, cache)
        snapshot_ts = cast(datetime | None, cache_obj.snapshot_date)
        monthly_growth = cache_obj.monthly_growth_rate
        growth_confidence = cache_obj.growth_confidence
        months_to_fi = cache_obj.months_to_fi
        return {
            "snapshot_date": snapshot_ts.isoformat() if snapshot_ts else None,
            "current_assets": float(cache_obj.current_assets),
            "annual_expense": float(cache_obj.annual_expense),
            "fire_target": float(cache_obj.fire_target),
            "progress_rate": float(cache_obj.progress_rate),
            "monthly_growth_rate": (
                float(monthly_growth) if monthly_growth is not None else None
            ),
            "growth_confidence": (
                float(growth_confidence) if growth_confidence is not None else None
            ),
            "months_to_fi": (float(months_to_fi) if months_to_fi is not None else None),
            "is_achievable": bool(cache_obj.is_achievable),
        }


__all__ = [
    "SNAPSHOT_CATEGORIES",
    "FireSnapshotRequest",
    "FireSnapshotResponse",
    "LinearSnapshotInterpolator",
    "SnapshotInterpolator",
    "SnapshotPoint",
]
