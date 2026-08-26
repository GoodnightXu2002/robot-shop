from models import Product, Review, User, db


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


def create_test_review(app):
    with app.app_context():
        user = User.query.filter_by(username="user").first()
        product = Product(
            name="后台评价测试机器人",
            category="测试分类",
            price=1,
            stock=1,
            description="用于后台评价删除测试的临时商品。",
            scene="测试场景",
            is_active=True,
        )
        db.session.add(product)
        db.session.flush()
        review = Review(
            user_id=user.id,
            product_id=product.id,
            rating=5,
            content="用于后台评价删除测试。",
            is_verified_purchase=False,
        )
        db.session.add(review)
        db.session.commit()
        return review.id


def test_admin_reviews_requires_login(client):
    response = client.get("/admin/reviews", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_reviews(client):
    login_regular_user(client)

    response = client.get("/admin/reviews", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_access_reviews_page(client):
    login_admin(client)

    response = client.get("/admin/reviews")

    assert response.status_code == 200


def test_admin_can_delete_review(client, app):
    review_id = create_test_review(app)
    login_admin(client)

    response = client.post(f"/admin/reviews/{review_id}/delete", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/reviews")
    with app.app_context():
        assert db.session.get(Review, review_id) is None
