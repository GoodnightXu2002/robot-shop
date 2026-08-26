from models import Consultation, Notification, User, db


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


def create_test_consultation(app):
    with app.app_context():
        user = User.query.filter_by(username="user").first()
        consultation = Consultation(
            user_id=user.id,
            name="测试咨询用户",
            contact="test-consultation@example.com",
            title="后台咨询测试",
            content="用于后台咨询状态更新测试。",
            status="待处理",
            admin_reply="",
        )
        db.session.add(consultation)
        db.session.commit()
        return consultation.id


def test_admin_consultations_requires_login(client):
    response = client.get("/admin/consultations", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_consultations(client):
    login_regular_user(client)

    response = client.get("/admin/consultations", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_access_consultations_page(client):
    login_admin(client)

    response = client.get("/admin/consultations")

    assert response.status_code == 200


def test_admin_can_update_consultation_status_and_reply(client, app):
    consultation_id = create_test_consultation(app)
    login_admin(client)

    response = client.post(
        f"/admin/consultations/{consultation_id}/status",
        data={"status": "已回复", "admin_reply": "这是后台测试回复。"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/consultations")
    with app.app_context():
        consultation = db.session.get(Consultation, consultation_id)
        notification = Notification.query.filter_by(
            user_id=consultation.user_id,
            title="咨询已回复",
            type="consultation",
        ).first()

        assert consultation.status == "已回复"
        assert consultation.admin_reply == "这是后台测试回复。"
        assert notification is not None
