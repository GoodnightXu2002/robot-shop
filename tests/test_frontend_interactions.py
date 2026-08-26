from models import Appointment, Consultation, Product, Review, db


def login_regular_user(client):
    return client.post(
        "/login",
        data={"username": "user", "password": "test-user-password"},
        follow_redirects=False,
    )


def create_reviewable_product(app):
    with app.app_context():
        product = Product(
            name="前台评价测试机器人",
            category="测试分类",
            price=1,
            stock=1,
            description="用于前台评价测试的临时商品。",
            scene="测试场景",
            is_active=True,
        )
        db.session.add(product)
        db.session.commit()
        return product.id


def test_add_review_requires_login(client, app):
    product_id = create_reviewable_product(app)

    response = client.post(
        f"/products/{product_id}/review",
        data={"rating": 5, "content": "未登录评价测试。"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logged_in_user_can_submit_review(client, app):
    product_id = create_reviewable_product(app)
    login_regular_user(client)

    response = client.post(
        f"/products/{product_id}/review",
        data={"rating": 5, "content": "这是一条前台评价测试。"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/products/{product_id}")
    with app.app_context():
        review = Review.query.filter_by(product_id=product_id).first()
        assert review is not None
        assert review.rating == 5
        assert review.content == "这是一条前台评价测试。"


def test_logged_in_user_can_access_consultations(client):
    login_regular_user(client)

    response = client.get("/consultations", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/appointments?consultation=1#service-support-consultation"
    )


def test_logged_in_user_can_submit_consultation(client, app):
    login_regular_user(client)

    response = client.post(
        "/consultations",
        data={
            "name": "前台咨询测试用户",
            "contact": "frontend-consultation@example.com",
            "title": "前台咨询测试",
            "content": "用于前台咨询提交测试。",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/appointments?consultation=1#service-support-consultation"
    )
    with app.app_context():
        consultation = Consultation.query.filter_by(title="前台咨询测试").first()
        assert consultation is not None
        assert consultation.status == "待处理"
        assert consultation.content == "用于前台咨询提交测试。"


def test_legacy_consultation_entry_redirects(client):
    login_regular_user(client)

    response = client.get("/consultation", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["Location"].endswith(
        "/appointments?consultation=1#service-support-consultation"
    )


def test_logged_in_user_can_submit_appointment(client, app):
    login_regular_user(client)

    response = client.post(
        "/appointments",
        data={
            "service_type": "安装调试",
            "appointment_date": "2026-06-15",
            "time_slot": "09:00-11:00",
            "address": "前台预约测试地址",
            "contact_name": "前台预约测试用户",
            "contact": "13900008888",
            "remark": "用于前台预约提交测试。",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/appointments")
    with app.app_context():
        appointment = Appointment.query.filter_by(contact_name="前台预约测试用户").first()
        assert appointment is not None
        assert appointment.status == "待确认"
        assert appointment.appointment_time == "2026-06-15 09:00-11:00"
