import pytest

from ai_assistant_service import build_ai_assistant_reply
from models import Product


def test_regular_user_login_flow_redirects_to_user_center(client):
    response = client.post(
        "/login",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/user/center" in response.headers["Location"]


def test_regular_user_login_allows_safe_relative_next(client):
    response = client.post(
        "/login?next=/cart",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cart")


def test_regular_user_login_blocks_external_next(client):
    response = client.post(
        "/login?next=https://evil.com",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user/center")


def test_regular_user_login_blocks_http_external_next(client):
    response = client.post(
        "/login?next=http://example.com",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/user/center")


def test_admin_login_flow_redirects_to_admin_dashboard(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "test-admin-password"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")


def test_admin_login_blocks_protocol_relative_next(client):
    response = client.post(
        "/login?next=//evil.com",
        data={"username": "admin", "password": "test-admin-password"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin")


def test_product_detail_page_is_accessible(client, app):
    with app.app_context():
        product = Product.query.filter_by(is_active=True).order_by(Product.id.asc()).first()

    response = client.get(f"/products/{product.id}")

    assert response.status_code == 200


def test_cart_requires_login(client):
    response = client.get("/cart", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


@pytest.mark.parametrize("message", [
    "推荐一款餐饮服务机器人",
    "推荐一款机器人",
    "有什么机器人适合商场",
    "推荐支持自动充电的机器人",
])
def test_ai_assistant_without_api_key_returns_local_response(client, monkeypatch, message):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post(
        "/api/ai-assistant/chat",
        json={"message": message, "page_url": "/products"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["reply"].startswith("根据您的需求，我优先推荐以下已上架产品：")
    assert payload["source"] == "local_rules"


@pytest.mark.parametrize("message", [
    "机器人无法正常充电",
    "机器人充不上电",
    "充电底座没有反应",
    "机器人无法充电",
    "机器人充电异常",
    "配送机器人无法充电",
    "Unitree G1 型号的机器人无法正常充电",
])
def test_ai_assistant_charging_fault_returns_local_troubleshooting(app, monkeypatch, message):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with app.test_request_context():
        payload = build_ai_assistant_reply(message, "/appointments", None, [])

    assert payload["source"] == "local_rules"
    assert all(term in payload["reply"] for term in ("电源", "充电底座", "充电触点", "重新放置", "重启"))
    assert "推荐" not in payload["reply"]
    assert payload["actions"] == [{"text": "提交服务预约", "url": "/appointments"}]
