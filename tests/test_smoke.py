def test_home_page_is_accessible(client):
    response = client.get("/")

    assert response.status_code == 200


def test_products_page_is_accessible(client):
    response = client.get("/products")

    assert response.status_code == 200


def test_login_page_is_accessible(client):
    response = client.get("/login")

    assert response.status_code == 200


def test_admin_page_requires_login(client):
    response = client.get("/admin")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
