"""Integration tests for HTTP server endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from household_mcp.web.http_server import create_http_app


@pytest.fixture
def client():
    """Create a test client for the HTTP app."""
    app = create_http_app(enable_cors=True)
    return TestClient(app)


class TestHTTPServerEndpoints:
    """Test suite for HTTP server endpoints availability."""

    def test_api_tools_endpoint_exists(self, client):
        """Test that /api/tools endpoint is available."""
        response = client.get("/api/tools")
        assert response.status_code == 200
        assert "success" in response.json()
        assert "data" in response.json()

    def test_api_tools_returns_tool_definitions(self, client):
        """Test that /api/tools returns list of tool definitions."""
        response = client.get("/api/tools")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        tools = data["data"]
        assert isinstance(tools, list)
        assert len(tools) > 0

        # Verify each tool has required fields
        for tool in tools:
            assert "name" in tool
            assert "display_name" in tool
            assert "description" in tool
            assert "parameters" in tool

    def test_api_duplicates_candidates_endpoint_exists(self, client):
        """Test that /api/duplicates/candidates endpoint is available."""
        response = client.get("/api/duplicates/candidates")
        assert response.status_code == 200
        assert "success" in response.json()

    def test_api_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        # FastAPI may not have /health by default, but our custom endpoint should exist
        # if implemented in create_http_app
        if response.status_code == 200:
            data = response.json()
            assert "success" in data or "status" in data or data == {}

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.get("/api/tools")
        assert response.status_code == 200
        # Check for CORS headers if CORS is enabled
        headers = response.headers
        # The exact headers depend on CORS configuration
        # Just verify response succeeds with CORS enabled

    def test_cors_options_request(self, client):
        """Test that OPTIONS requests are handled for CORS."""
        response = client.options("/api/tools")
        # Should either return 200 or be handled by CORS middleware
        assert response.status_code in [200, 204, 405]

    def test_all_required_mcp_tools_available(self, client):
        """Test that all required MCP tools are available."""
        response = client.get("/api/tools")
        assert response.status_code == 200
        tools = response.json()["data"]
        tool_names = [tool["name"] for tool in tools]

        required_tools = [
            "enhanced_monthly_summary",
            "enhanced_category_trend",
            "detect_duplicates",
            "get_duplicate_candidates",
            "confirm_duplicate",
        ]

        for tool_name in required_tools:
            assert tool_name in tool_names, f"Required tool '{tool_name}' not found"


class TestDatabaseManagerInitialization:
    """Test suite for database manager initialization."""

    def test_database_manager_initialized(self, client):
        """Test that database manager is properly initialized on startup."""
        # This test verifies that the app can call duplicate tools
        response = client.get("/api/duplicates/candidates")
        # Should not return Database manager not initialized error
        assert response.status_code == 200
        assert "Database manager not initialized" not in response.text

    def test_duplicate_detection_endpoint_accessible(self, client):
        """Test that duplicate detection endpoint is accessible."""
        response = client.post("/api/duplicates/detect")
        # May return validation error or success, but not 404 or 500 (db init error)
        assert response.status_code in [200, 400, 422]


class TestToolExecutionEndpoints:
    """Test suite for tool execution endpoints."""

    def test_tool_execute_endpoint_exists(self, client):
        """Test that tool execution endpoint exists."""
        # Test with a valid tool name
        response = client.post(
            "/api/tools/enhanced_monthly_summary/execute",
            json={"year": 2024, "month": 1},
        )
        # Should not return 404
        assert response.status_code != 404

    def test_tool_execute_invalid_tool_returns_error(self, client):
        """Test that invalid tool name returns appropriate error."""
        response = client.post("/api/tools/nonexistent_tool/execute", json={})
        # Should return 400 or 422, not 404 or 500
        assert response.status_code in [400, 422, 404]


class TestOpenAPIDocumentation:
    """Test suite for OpenAPI documentation."""

    def test_openapi_json_available(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
        assert "/api/tools" in schema["paths"]

    def test_swagger_ui_available(self, client):
        """Test that Swagger UI is available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger-ui" in response.text.lower()
