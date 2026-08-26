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


def test_admin_dashboard_requires_login(client):
    response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_dashboard(client):
    login_regular_user(client)

    response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_access_admin_dashboard(client):
    login_admin(client)

    response = client.get("/admin")

    assert response.status_code == 200


def test_admin_can_access_statistics_page(client):
    login_admin(client)

    response = client.get("/admin/statistics")

    assert response.status_code == 200
