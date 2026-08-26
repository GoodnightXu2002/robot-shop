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


def test_ai_assistant_without_api_key_returns_local_response(client):
    response = client.post(
        "/api/ai-assistant/chat",
        json={"message": "推荐一款餐饮服务机器人", "page_url": "/products"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["reply"]
    assert payload["source"] in {"local_rules", "error_fallback"}
