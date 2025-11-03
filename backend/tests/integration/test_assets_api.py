"""Test asset API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from household_mcp.database.manager import DatabaseManager
from household_mcp.assets.models import AssetRecordRequest


@pytest.fixture
def temp_db_setup(tmp_path):
    """Create temporary database with initial data."""
    db_path = str(tmp_path / "test_api.db")
    db = DatabaseManager(db_path=db_path)
    db.initialize_database()

    # Create test data
    from household_mcp.assets.manager import AssetManager

    with db.session_scope() as session:
        manager = AssetManager(session)

        # Add test records
        for i in range(3):
            request = AssetRecordRequest(
                record_date=datetime(2025, 1, 28),
                asset_class_id=1,
                sub_asset_name=f"テスト資産{i+1}",
                amount=100000 * (i + 1),
            )
            manager.create_record(request)

    yield db
    db.close()


class TestAssetAPIEndpoints:
    """Test asset API endpoints."""

    def test_get_asset_classes_endpoint(self, temp_db_setup):
        """Test GET /api/assets/classes endpoint."""
        from household_mcp.web.http_server import create_http_app

        app = create_http_app(enable_cors=True)
        client = TestClient(app)

        response = client.get("/api/assets/classes")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "count" in data
        assert data["count"] == 5
        assert len(data["data"]) == 5

        # Check that all 5 asset classes are present
        names = [c["name"] for c in data["data"]]
        assert "cash" in names
        assert "stocks" in names
        assert "funds" in names
        assert "realestate" in names
        assert "pension" in names

        # Check data structure
        for asset_class in data["data"]:
            assert "id" in asset_class
            assert "name" in asset_class
            assert "display_name" in asset_class
            assert "icon" in asset_class
            assert "created_at" in asset_class

    def test_get_asset_classes_display_names(self, temp_db_setup):
        """Test that asset classes have correct display names."""
        from household_mcp.web.http_server import create_http_app

        app = create_http_app(enable_cors=True)
        client = TestClient(app)

        response = client.get("/api/assets/classes")
        data = response.json()

        # Create a map of names to display names
        display_map = {c["name"]: c["display_name"] for c in data["data"]}

        assert display_map["cash"] == "現金"
        assert display_map["stocks"] == "株"
        assert display_map["funds"] == "投資信託"
        assert display_map["realestate"] == "不動産"
        assert display_map["pension"] == "年金"

    def test_get_asset_classes_icons(self, temp_db_setup):
        """Test that asset classes have correct icons."""
        from household_mcp.web.http_server import create_http_app

        app = create_http_app(enable_cors=True)
        client = TestClient(app)

        response = client.get("/api/assets/classes")
        data = response.json()

        # Create a map of names to icons
        icon_map = {c["name"]: c["icon"] for c in data["data"]}

        assert icon_map["cash"] == "💰"
        assert icon_map["stocks"] == "📈"
        assert icon_map["funds"] == "📊"
        assert icon_map["realestate"] == "🏠"
        assert icon_map["pension"] == "🎯"
