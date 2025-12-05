"""
API endpoint tests.
"""

from __future__ import annotations

from datetime import datetime


from fastapi.testclient import TestClient


def test_get_last_message_returns_200(client: TestClient, sample_messages):
    response = client.get("/stats/last")
    assert response.status_code == 200


def test_get_last_n_messages_returns_200(client: TestClient, sample_messages):
    response = client.get("/stats/last/5")
    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_get_last_n_messages_validates_count(client: TestClient):
    response = client.get("/stats/last/0")
    assert response.status_code == 422


def test_get_today_stats_returns_200(client: TestClient, sample_messages):
    response = client.get("/stats/today")
    assert response.status_code == 200


def test_get_today_detailed_returns_hourly(
    client: TestClient, sample_messages
):
    response = client.get("/stats/today/detailed")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_stats_by_date_returns_200(client: TestClient, sample_messages):
    today = datetime.utcnow().date().isoformat()
    response = client.get(f"/stats/{today}")
    assert response.status_code == 200


def test_post_subscribe_creates_subscription(client: TestClient, sample_users):
    user_id = sample_users[0].user_id
    response = client.post(f"/subscribe/{user_id}/daily_avg")
    assert response.status_code == 201


def test_post_subscribe_validates_type(client: TestClient, sample_users):
    user_id = sample_users[0].user_id
    response = client.post(f"/subscribe/{user_id}/invalid_type")
    assert response.status_code in (400, 422)


def test_delete_subscribe_removes_subscriptions(
    client: TestClient, sample_users
):
    user_id = sample_users[0].user_id
    client.post(f"/subscribe/{user_id}/daily_avg")
    response = client.delete(f"/subscribe/{user_id}")
    assert response.status_code == 200


def test_get_subscriptions_returns_list(client: TestClient):
    response = client.get("/subscriptions")
    assert response.status_code == 200


def test_post_mock_message_creates_message(client: TestClient, sample_users):
    user = sample_users[0]
    payload = {
        "sender_id": user.user_id,
        "sender_name": user.username,
        "gateway_count": 3,
        "rssi": -70,
        "snr": 5.1,
        "payload": "hello",
        "timestamp": datetime.utcnow().isoformat(),
    }
    response = client.post("/mock/message", json=payload)
    assert response.status_code == 200


def test_post_mock_message_validates_input(client: TestClient):
    response = client.post("/mock/message", json={})
    assert response.status_code == 422


def test_get_health_returns_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200


def test_invalid_date_format_returns_400(client: TestClient):
    response = client.get("/stats/not-a-date")
    assert response.status_code == 400


def test_invalid_subscription_type_returns_400(
    client: TestClient, sample_users
):
    user_id = sample_users[0].user_id
    response = client.post(f"/subscribe/{user_id}/invalid-type")
    assert response.status_code in (400, 422)


def test_nonexistent_resource_returns_404(client: TestClient):
    response = client.get("/stats/user/9999/last")
    assert response.status_code == 404


def test_server_error_returns_500(monkeypatch, client: TestClient):
    def raise_error(*args, **kwargs):
        raise ValueError("boom")

    monkeypatch.setattr(
        "src.services.stats_service.StatsService.get_today_stats", raise_error
    )
    response = client.get("/stats/today")
    assert response.status_code == 500
