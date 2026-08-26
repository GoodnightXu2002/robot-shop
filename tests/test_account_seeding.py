from werkzeug.security import check_password_hash

from models import User, db
from services.database import seed_users


def test_seed_users_requires_complete_credentials(app, monkeypatch):
    monkeypatch.setenv("ROBOT_SHOP_DEMO_ADMIN_USERNAME", "incomplete-admin")
    monkeypatch.delenv("ROBOT_SHOP_DEMO_ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("ROBOT_SHOP_DEMO_USER_USERNAME", "incomplete-user")
    monkeypatch.setenv("ROBOT_SHOP_DEMO_USER_PASSWORD", "   ")

    with app.app_context():
        seed_users()
        db.session.commit()

        assert User.query.filter_by(username="incomplete-admin").first() is None
        assert User.query.filter_by(username="incomplete-user").first() is None


def test_seed_users_does_not_overwrite_existing_account(app, monkeypatch):
    with app.app_context():
        admin = User.query.filter_by(username="admin").one()
        original_password_hash = admin.password_hash
        admin.email = "existing-admin@example.com"
        admin.phone = "18800000000"
        db.session.commit()

        monkeypatch.setenv("ROBOT_SHOP_DEMO_ADMIN_PASSWORD", "replacement-password")
        seed_users()
        db.session.commit()

        admin = User.query.filter_by(username="admin").one()
        assert admin.password_hash == original_password_hash
        assert check_password_hash(admin.password_hash, "test-admin-password")
        assert not check_password_hash(admin.password_hash, "replacement-password")
        assert admin.email == "existing-admin@example.com"
        assert admin.phone == "18800000000"
        assert admin.is_admin is True
