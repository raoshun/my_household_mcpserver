# -*- coding: utf-8 -*-
"""トレンド分析機能の統合テスト (FR-019)

NOTE: These tests require the 'web' (and 'streaming') extras.
They are skipped automatically when FastAPI or web modules are unavailable.
"""

import pytest

# Check if web dependencies are available
try:
    from fastapi.testclient import TestClient

    from household_mcp.web.http_server import create_http_app

    HAS_WEB = True
except Exception:  # pragma: no cover - import guard for optional extras
    HAS_WEB = False
    TestClient = None  # type: ignore[assignment]
    create_http_app = None  # type: ignore[assignment]

pytestmark = pytest.mark.skipif(
    not HAS_WEB, reason="requires web/streaming extras (fastapi)"
)


@pytest.fixture
def client():  # type: ignore[no-untyped-def]
    app = create_http_app()
    return TestClient(app)


class TestTrendAPI:
    """トレンドAPIテスト"""

    def test_monthly_summary_success(self, client):  # type: ignore[no-untyped-def]
        """月次サマリー正常系"""
        response = client.get(
            "/api/trend/monthly_summary",
            params={
                "start_year": 2025,
                "start_month": 4,
                "end_year": 2025,
                "end_month": 6,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 3

    def test_category_breakdown_success(self, client):  # type: ignore[no-untyped-def]
        """カテゴリ別トレンド正常系"""
        response = client.get(
            "/api/trend/category_breakdown",
            params={
                "start_year": 2025,
                "start_month": 4,
                "end_year": 2025,
                "end_month": 6,
                "top_n": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["categories"]) <= 5

    def test_invalid_date_range(self, client):  # type: ignore[no-untyped-def]
        """無効な日付範囲"""
        response = client.get(
            "/api/trend/monthly_summary",
            params={
                "start_year": 2025,
                "start_month": 6,
                "end_year": 2025,
                "end_month": 4,
            },
        )
        assert response.status_code == 400
