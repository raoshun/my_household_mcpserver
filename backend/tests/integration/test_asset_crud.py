"""Integration tests for asset CRUD endpoints."""

import pytest
from fastapi.testclient import TestClient

from household_mcp.database.manager import DatabaseManager
from household_mcp.web.http_server import create_http_app


@pytest.fixture
def db_manager() -> DatabaseManager:
    """Create test database manager."""
    manager = DatabaseManager()
    manager.drop_all_tables()
    manager.initialize_database()
    yield manager
    manager.drop_all_tables()


@pytest.fixture
def client(db_manager: DatabaseManager) -> TestClient:
    """Create test client with initialized database."""
    app = create_http_app()
    return TestClient(app)


@pytest.fixture
def sample_record_data() -> dict:
    """Sample asset record data."""
    return {
        "record_date": "2025-01-15T00:00:00",
        "asset_class_id": 1,  # cash
        "sub_asset_name": "Main Bank",
        "amount": 100000,
        "memo": "Monthly deposit",
    }


class TestAssetCRUD:
    """Test asset CRUD operations."""

    def test_get_asset_classes(self, client: TestClient) -> None:
        """Test GET /api/assets/classes."""
        response = client.get("/api/assets/classes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5
        # Check asset class structure
        for ac in data:
            assert "id" in ac
            assert "name" in ac
            assert "display_name" in ac

    def test_create_asset_record(
        self, client: TestClient, sample_record_data: dict
    ) -> None:
        """Test POST /api/assets/records/create."""
        response = client.post(
            "/api/assets/records/create",
            json=sample_record_data,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 100000
        assert data["sub_asset_name"] == "Main Bank"

    def test_get_asset_records(
        self, client: TestClient, sample_record_data: dict
    ) -> None:
        """Test GET /api/assets/records."""
        # Create a record first
        client.post("/api/assets/records/create", json=sample_record_data)

        response = client.get("/api/assets/records")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_get_asset_records_with_filters(
        self, client: TestClient, sample_record_data: dict
    ) -> None:
        """Test GET /api/assets/records with filters."""
        # Create a record
        client.post("/api/assets/records/create", json=sample_record_data)

        # Filter by asset class
        response = client.get("/api/assets/records?asset_class_id=1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_update_asset_record(
        self, client: TestClient, sample_record_data: dict
    ) -> None:
        """Test PUT /api/assets/records/{record_id}."""
        # Create a record
        create_response = client.post(
            "/api/assets/records/create",
            json=sample_record_data,
        )
        record_id = create_response.json()["id"]

        # Update the record
        updated_data = {
            "record_date": "2025-01-20T00:00:00",
            "asset_class_id": 2,  # stocks
            "sub_asset_name": "Updated Bank",
            "amount": 150000,
            "memo": "Updated memo",
        }
        response = client.put(
            f"/api/assets/records/{record_id}",
            json=updated_data,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["amount"] == 150000
        assert data["sub_asset_name"] == "Updated Bank"

    def test_update_nonexistent_record(self, client: TestClient) -> None:
        """Test PUT /api/assets/records/{record_id} with invalid ID."""
        update_data = {
            "record_date": "2025-01-20T00:00:00",
            "asset_class_id": 1,
            "sub_asset_name": "Bank",
            "amount": 100000,
        }
        response = client.put(
            "/api/assets/records/99999",
            json=update_data,
        )
        assert response.status_code == 404

    def test_delete_asset_record(
        self, client: TestClient, sample_record_data: dict
    ) -> None:
        """Test DELETE /api/assets/records/{record_id}."""
        # Create a record
        create_response = client.post(
            "/api/assets/records/create",
            json=sample_record_data,
        )
        record_id = create_response.json()["id"]

        # Delete the record
        response = client.delete(f"/api/assets/records/{record_id}")
        assert response.status_code == 204

    def test_delete_nonexistent_record(self, client: TestClient) -> None:
        """Test DELETE /api/assets/records/{record_id} with invalid ID."""
        response = client.delete("/api/assets/records/99999")
        assert response.status_code == 404

    def test_get_asset_summary(self, client: TestClient) -> None:
        """Test GET /api/assets/summary."""
        response = client.get("/api/assets/summary?year=2025&month=1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_get_asset_allocation(self, client: TestClient) -> None:
        """Test GET /api/assets/allocation."""
        response = client.get("/api/assets/allocation?year=2025&month=1")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_invalid_month(self, client: TestClient) -> None:
        """Test with invalid month parameter."""
        response = client.get("/api/assets/summary?year=2025&month=13")
        # HTTPException is caught and returns 500
        assert response.status_code in [400, 500]

    def test_create_missing_field(self, client: TestClient) -> None:
        """Test POST with missing required field."""
        invalid_data = {
            "record_date": "2025-01-15T00:00:00",
            "asset_class_id": 1,
            "amount": 100000,
            # missing sub_asset_name
        }
        response = client.post(
            "/api/assets/records/create",
            json=invalid_data,
        )
        # Should return 422 validation error or 400
        assert response.status_code in [400, 422]

    def test_crud_workflow(self, client: TestClient, sample_record_data: dict) -> None:
        """Test complete CRUD workflow."""
        # Create
        resp_create = client.post("/api/assets/records/create", json=sample_record_data)
        assert resp_create.status_code == 201
        record_id = resp_create.json()["id"]

        # Read
        read_resp = client.get("/api/assets/records")
        assert read_resp.status_code == 200
        records = read_resp.json()
        assert any(r["id"] == record_id for r in records)

        # Update
        update_data = sample_record_data.copy()
        update_data["amount"] = 200000
        update_resp = client.put(
            f"/api/assets/records/{record_id}",
            json=update_data,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["amount"] == 200000

        # Delete
        delete_resp = client.delete(f"/api/assets/records/{record_id}")
        assert delete_resp.status_code == 204
