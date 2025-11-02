# -*- coding: utf-8 -*-
"""トレンド分析機能の統合テスト (FR-019)"""

import pytest
from fastapi.testclient import TestClient

from household_mcp.web.http_server import create_http_app


@pytest.fixture
def client():
    app = create_http_app()
    return TestClient(app)


class TestTrendAPI:
    """トレンドAPIテスト"""

    def test_monthly_summary_success(self, client):
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

    def test_category_breakdown_success(self, client):
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

    def test_invalid_date_range(self, client):
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
