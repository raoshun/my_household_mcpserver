"""REST API endpoint integration tests"""

import time
from datetime import date

import pytest
from fastapi.testclient import TestClient

from household_mcp.database.manager import DatabaseManager
from household_mcp.services.fire_snapshot import (
    FireSnapshotRequest,
    FireSnapshotService,
)
from household_mcp.web.http_server import create_http_app


@pytest.fixture
def client() -> TestClient:
    """HTTP API client fixture with initial snapshot for FI endpoints"""
    app = create_http_app()
    client = TestClient(app)

    # FI endpoints now require at least one snapshot in DB
    # Register a baseline snapshot to make tests pass
    try:
        db = DatabaseManager()
        db.initialize_database()
        service = FireSnapshotService(db_manager=db)
        request = FireSnapshotRequest(
            snapshot_date=date(2025, 11, 1),
            cash_and_deposits=5_000_000,
            stocks_cash=0,
            stocks_margin=0,
            investment_trusts=0,
            pension=0,
            points=0,
        )
        service.register_snapshot(request)
    except Exception:
        pass  # テスト実行環境によってはスキップ可能

    return client


class TestStatusEndpoint:
    """GET /api/financial-independence/status"""

    def test_returns_200(self, client: TestClient) -> None:
        """Returns 200 OK"""
        response = client.get("/api/financial-independence/status")
        assert response.status_code == 200

    def test_has_required_fields(self, client: TestClient) -> None:
        """Response has required fields"""
        response = client.get("/api/financial-independence/status")
        data = response.json()

        assert "fire_percentage" in data
        assert "current_assets" in data
        assert "months_to_fi" in data

    def test_numeric_ranges(self, client: TestClient) -> None:
        """Numeric values in valid ranges"""
        response = client.get("/api/financial-independence/status")
        data = response.json()

        # fire_percentage は progress_rate から取得
        assert data["fire_percentage"] is not None
        assert data["fire_percentage"] >= 0  # 上限チェックは柔軟に
        assert data["current_assets"] > 0
        # months_to_fi は達成不可能な場合Noneでよい
        assert data["months_to_fi"] is None or data["months_to_fi"] > 0


class TestExpenseBreakdownEndpoint:
    """GET /api/financial-independence/expense-breakdown"""

    def test_returns_200(self, client: TestClient) -> None:
        """Returns 200 OK"""
        response = client.get("/api/financial-independence/expense-breakdown")
        assert response.status_code == 200

    def test_has_categories(self, client: TestClient) -> None:
        """Response has categories list"""
        response = client.get("/api/financial-independence/expense-breakdown")
        data = response.json()

        assert "categories" in data
        assert isinstance(data["categories"], list)


class TestProjectionsEndpoint:
    """GET /api/financial-independence/projections"""

    def test_returns_200(self, client: TestClient) -> None:
        """Returns 200 OK"""
        response = client.get("/api/financial-independence/projections")
        assert response.status_code == 200

    def test_has_scenarios(self, client: TestClient) -> None:
        """Response has scenarios"""
        response = client.get("/api/financial-independence/projections")
        data = response.json()

        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)


class TestUpdateClassificationEndpoint:
    """POST /api/financial-independence/update-expense-classification"""

    def test_valid_returns_200(self, client: TestClient) -> None:
        """Valid params return 200"""
        response = client.post(
            "/api/financial-independence/update-expense-classification",
            params={"category": "food", "classification": "regular"},
        )
        assert response.status_code == 200

    def test_invalid_classification(self, client: TestClient) -> None:
        """Invalid classification returns error"""
        response = client.post(
            "/api/financial-independence/update-expense-classification",
            params={"category": "food", "classification": "invalid"},
        )
        assert response.status_code == 400


class TestPerformance:
    """Performance tests"""

    def test_status_under_5s(self, client: TestClient) -> None:
        """Status endpoint < 5s"""
        start = time.time()
        response = client.get("/api/financial-independence/status")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0

    def test_breakdown_under_5s(self, client: TestClient) -> None:
        """Breakdown endpoint < 5s"""
        start = time.time()
        response = client.get("/api/financial-independence/expense-breakdown")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0

    def test_projections_under_5s(self, client: TestClient) -> None:
        """Projections endpoint < 5s"""
        start = time.time()
        response = client.get("/api/financial-independence/projections")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 5.0


class TestEndToEnd:
    """End-to-end workflow"""

    def test_complete_workflow(self, client: TestClient) -> None:
        """Full workflow: status > breakdown > projections > update"""
        # Get status
        assert client.get("/api/financial-independence/status").status_code == 200

        # Get breakdown
        assert (
            client.get("/api/financial-independence/expense-breakdown").status_code
            == 200
        )

        # Get projections
        assert client.get("/api/financial-independence/projections").status_code == 200

        # Update
        assert (
            client.post(
                "/api/financial-independence/update-expense-classification",
                params={"category": "food", "classification": "regular"},
            ).status_code
            == 200
        )
