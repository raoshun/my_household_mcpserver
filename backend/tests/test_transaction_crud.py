"""Tests for Transaction CRUD API (TASK-1303)."""

import pytest
from fastapi.testclient import TestClient


class TestTransactionCRUD:
    """Transaction CRUD API テストスイート."""

    @pytest.fixture
    def client(self, app):
        """FastAPI TestClient fixture."""
        return TestClient(app)

    def test_create_transaction(self, client):
        """取引作成エンドポイントのテスト."""
        payload = {
            "date": "2025-11-08T00:00:00",
            "amount": 1000.0,
            "description": "テスト取引",
            "category_major": "食費",
            "category_minor": "外食",
            "account": "クレジットカード",
            "memo": "テストメモ",
            "is_target": 1,
        }

        response = client.post("/api/transactions/create", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == 1000.0
        assert data["description"] == "テスト取引"
        assert data["category_major"] == "食費"

    def test_list_transactions(self, client):
        """取引一覧エンドポイントのテスト."""
        response = client.get("/api/transactions/list")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 100  # デフォルトlimit

    def test_list_transactions_with_filter(self, client):
        """取引一覧フィルタのテスト."""
        response = client.get(
            "/api/transactions/list",
            params={
                "start_date": "2022-01-01T00:00:00",
                "end_date": "2022-01-31T23:59:59",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_transaction(self, client):
        """取引詳細取得エンドポイントのテスト."""
        response = client.get("/api/transactions/1")
        # Transaction ID 1 が存在する場合
        if response.status_code == 200:
            data = response.json()
            assert data["id"] == 1
            assert "date" in data
            assert "amount" in data

    def test_get_transaction_not_found(self, client):
        """取引が見つからない場合のテスト."""
        response = client.get("/api/transactions/999999")
        assert response.status_code == 404

    def test_update_transaction(self, client):
        """取引更新エンドポイントのテスト."""
        # 先に取引を作成
        payload = {
            "date": "2025-11-08T00:00:00",
            "amount": 1000.0,
            "description": "テスト取引",
            "category_major": "食費",
            "category_minor": "外食",
            "account": "クレジットカード",
            "memo": "テストメモ",
            "is_target": 1,
        }
        create_response = client.post("/api/transactions/create", json=payload)
        assert create_response.status_code == 201
        transaction_id = create_response.json()["id"]

        # 更新
        update_payload = {
            "date": "2025-11-08T00:00:00",
            "amount": 2000.0,
            "description": "更新後の取引",
            "category_major": "食費",
            "category_minor": "外食",
            "account": "クレジットカード",
            "memo": "更新後メモ",
            "is_target": 1,
        }
        update_response = client.put(
            f"/api/transactions/{transaction_id}", json=update_payload
        )
        assert update_response.status_code == 200
        data = update_response.json()
        assert data["amount"] == 2000.0
        assert data["description"] == "更新後の取引"

    def test_delete_transaction(self, client):
        """取引削除エンドポイントのテスト."""
        # 先に取引を作成
        payload = {
            "date": "2025-11-08T00:00:00",
            "amount": 1000.0,
            "description": "テスト取引",
            "category_major": "食費",
            "category_minor": "外食",
            "account": "クレジットカード",
            "memo": "テストメモ",
            "is_target": 1,
        }
        create_response = client.post("/api/transactions/create", json=payload)
        assert create_response.status_code == 201
        transaction_id = create_response.json()["id"]

        # 削除
        delete_response = client.delete(f"/api/transactions/{transaction_id}")
        assert delete_response.status_code == 204

        # 削除確認
        get_response = client.get(f"/api/transactions/{transaction_id}")
        assert get_response.status_code == 404

    def test_list_with_pagination(self, client):
        """ページネーションのテスト."""
        response = client.get(
            "/api/transactions/list", params={"limit": 10, "offset": 0}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10
