from models import Product, db


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


def first_active_product(app):
    with app.app_context():
        return Product.query.filter_by(is_active=True).order_by(Product.id.asc()).first()


def create_deletable_product(app):
    with app.app_context():
        product = Product(
            name="测试可删除机器人",
            category="测试分类",
            price=1,
            stock=1,
            description="用于后台删除测试的临时商品。",
            scene="测试场景",
            is_active=True,
        )
        db.session.add(product)
        db.session.commit()
        return product.id


def test_admin_products_requires_login(client):
    response = client.get("/admin/products", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_products(client):
    login_regular_user(client)

    response = client.get("/admin/products", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_access_products_page(client):
    login_admin(client)

    response = client.get("/admin/products")

    assert response.status_code == 200


def test_admin_can_access_new_product_page(client):
    login_admin(client)

    response = client.get("/admin/products/new")

    assert response.status_code == 200


def test_admin_can_access_edit_product_page(client, app):
    product = first_active_product(app)
    login_admin(client)

    response = client.get(f"/admin/products/{product.id}/edit")

    assert response.status_code == 200


def test_admin_can_delete_product_without_server_error(client, app):
    product_id = create_deletable_product(app)
    login_admin(client)

    response = client.post(f"/admin/products/{product_id}/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/products")
    with app.app_context():
        assert db.session.get(Product, product_id) is None
