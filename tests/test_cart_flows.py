from models import CartItem, Product, Wishlist


def login_regular_user(client):
    return client.post(
        "/login",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )


def first_active_product(app):
    with app.app_context():
        return Product.query.filter_by(is_active=True).order_by(Product.id.asc()).first()


def test_logged_in_user_can_access_cart_page(client):
    login_regular_user(client)

    response = client.get("/cart")

    assert response.status_code == 200


def test_add_cart_requires_login(client, app):
    product = first_active_product(app)

    response = client.post(f"/cart/add/{product.id}", data={"quantity": 1}, follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logged_in_user_can_add_product_to_cart(client, app):
    product = first_active_product(app)
    login_regular_user(client)

    response = client.post(f"/cart/add/{product.id}", data={"quantity": 1}, follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/cart")
    with app.app_context():
        cart_item = CartItem.query.filter_by(product_id=product.id).first()
        assert cart_item is not None
        assert cart_item.quantity >= 1


def test_logged_in_user_can_call_wishlist_add(client, app):
    product = first_active_product(app)
    login_regular_user(client)

    response = client.post(f"/wishlist/add/{product.id}", follow_redirects=False)

    assert response.status_code == 302
    with app.app_context():
        wishlist_item = Wishlist.query.filter_by(product_id=product.id).first()
        assert wishlist_item is not None
