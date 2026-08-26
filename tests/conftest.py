import pytest

from app import create_app, init_database


@pytest.fixture()
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("TEST_DATABASE_URL", f"sqlite:///{tmp_path / 'test_robot_shop.db'}")
    monkeypatch.setenv("ROBOT_SHOP_DEMO_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ROBOT_SHOP_DEMO_ADMIN_PASSWORD", "test-admin-password")
    monkeypatch.setenv("ROBOT_SHOP_DEMO_USER_USERNAME", "user")
    monkeypatch.setenv("ROBOT_SHOP_DEMO_USER_PASSWORD", "test-user-password")
    test_app = create_app()
    test_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        OPENAI_API_KEY="",
        OPENAI_MODEL="gpt-4o-mini",
    )
    init_database(test_app)
    return test_app


@pytest.fixture()
def client(app):
    with app.test_client() as test_client:
        yield test_client
