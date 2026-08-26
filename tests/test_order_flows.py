from models import Order, Product, db


def login_regular_user(client):
    return client.post(
        "/login",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )


def first_active_product(app):
    with app.app_context():
        return Product.query.filter(Product.is_active == True, Product.stock > 0).order_by(Product.id.asc()).first()


def test_orders_page_requires_login(client):
    response = client.get("/orders", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logged_in_user_can_create_order_and_stock_decreases(client, app):
    product = first_active_product(app)
    original_stock = product.stock
    login_regular_user(client)

    response = client.post(f"/products/{product.id}/order", data={"quantity": 1}, follow_redirects=False)

    assert response.status_code == 302
    assert "/orders/" in response.headers["Location"]
    assert response.headers["Location"].endswith("/payment")
    with app.app_context():
        order = Order.query.filter_by(product_id=product.id).order_by(Order.id.desc()).first()
        updated_product = db.session.get(Product, product.id)
        assert order is not None
        assert order.quantity == 1
        assert order.status == "待支付"
        assert updated_product.stock == original_stock - 1


def test_payment_confirmation_updates_order_status(client, app):
    product = first_active_product(app)
    login_regular_user(client)
    client.post(f"/products/{product.id}/order", data={"quantity": 1}, follow_redirects=False)
    with app.app_context():
        order = Order.query.filter_by(product_id=product.id).order_by(Order.id.desc()).first()
        order_id = order.id

    response = client.post(f"/orders/{order_id}/payment/confirm", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/orders/{order_id}")
    with app.app_context():
        paid_order = db.session.get(Order, order_id)
        assert paid_order.status == "待发货"
        assert paid_order.logistics_status == "支付成功"
        assert paid_order.paid_at is not None
