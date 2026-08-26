def login_regular_user(client):
    return client.post(
        "/login",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )


def login_admin(client):
    return client.post(
        "/login",
        data={"username": "admin", "password": "test-admin-password"},
        follow_redirects=False,
    )


def test_admin_users_requires_login(client):
    response = client.get("/admin/users", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_users(client):
    login_regular_user(client)

    response = client.get("/admin/users", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_access_users_page(client):
    login_admin(client)

    response = client.get("/admin/users")

    assert response.status_code == 200


def test_admin_users_page_renders_seeded_users(client):
    login_admin(client)

    response = client.get("/admin/users")

    assert response.status_code == 200
    assert "admin".encode("utf-8") in response.data
    assert "admin@robot-shop.local".encode("utf-8") in response.data
    assert "user".encode("utf-8") in response.data
    assert "user@robot-shop.local".encode("utf-8") in response.data
