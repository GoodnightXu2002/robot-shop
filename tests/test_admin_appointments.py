from models import Appointment, Notification, User, db


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


def create_test_appointment(app):
    with app.app_context():
        user = User.query.filter_by(username="user").first()
        appointment = Appointment(
            user_id=user.id,
            service_type="安装调试",
            appointment_date="2026-06-01",
            time_slot="09:00-11:00",
            appointment_time="2026-06-01 09:00-11:00",
            address="测试预约地址",
            contact_name="测试预约用户",
            contact="13900009999",
            remark="用于后台预约状态更新测试。",
            process_note="",
            status="待确认",
        )
        db.session.add(appointment)
        db.session.commit()
        return appointment.id


def test_admin_appointments_requires_login(client):
    response = client.get("/admin/appointments", follow_redirects=False)

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_appointments(client):
    login_regular_user(client)

    response = client.get("/admin/appointments", follow_redirects=False)

    assert response.status_code == 403


def test_admin_can_access_appointments_page(client):
    login_admin(client)

    response = client.get("/admin/appointments")

    assert response.status_code == 200


def test_admin_can_update_appointment_status_and_process_note(client, app):
    appointment_id = create_test_appointment(app)
    login_admin(client)

    response = client.post(
        f"/admin/appointments/{appointment_id}/status",
        data={"status": "已确认", "process_note": "已安排工程师跟进。"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/admin/appointments")
    with app.app_context():
        appointment = db.session.get(Appointment, appointment_id)
        notification = Notification.query.filter_by(
            user_id=appointment.user_id,
            title="预约状态更新",
            type="appointment",
        ).first()

        assert appointment.status == "已确认"
        assert appointment.process_note == "已安排工程师跟进。"
        assert notification is not None
