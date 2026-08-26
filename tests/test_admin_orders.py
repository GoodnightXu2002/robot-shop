from datetime import datetime

from models import Order, Product, User, db


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


def create_test_order(app):
    with app.app_context():
        user = User.query.filter_by(username="user").first()
        product = Product.query.filter(Product.is_active == True, Product.stock > 0).order_by(Product.id.asc()).first()
        original_stock = product.stock
        original_sales = product.sales
        order = Order(
            order_no="TEST-ADMIN-ORDER",
            user_id=user.id,
            product_id=product.id,
            quantity=1,
            total_price=product.price,
            status="待支付",
            logistics_status="订单已提交",
            created_at=datetime.now(),
        )
        db.session.add(order)
        db.session.commit()
        return order.id, product.id, original_stock, original_sales


def test_admin_orders_requires_login(client):
    response = client.get("/admin/orders", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_orders(client):
    login_regular_user(client)

    response = client.get("/admin/orders", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_access_orders_page(client):
    login_admin(client)

    response = client.get("/admin/orders")

    assert response.status_code == 200


def test_admin_can_update_order_status_without_changing_product_counts(client, app):
    order_id, product_id, original_stock, original_sales = create_test_order(app)
    login_admin(client)

    response = client.post(
        f"/admin/orders/{order_id}/status",
        data={"status": "已发货", "logistics_status": "已发货"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/orders")
    with app.app_context():
        order = db.session.get(Order, order_id)
        product = db.session.get(Product, product_id)
        assert order.status == "已发货"
        assert order.logistics_status == "已发货"
        assert product.stock == original_stock
        assert product.sales == original_sales
