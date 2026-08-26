from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from app import create_app, run_debug_enabled
from config import BASE_DIR
from models import db
from scripts.check_project import configured_database_path


def database_path(app):
    return Path(make_url(app.config["SQLALCHEMY_DATABASE_URI"]).database)


def engine_database_path(app):
    with app.app_context():
        return Path(db.engine.url.database)


def test_development_config_can_create_app_without_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    app = create_app()

    assert app.config["SECRET_KEY"] == "robot-shop-dev-secret-key"
    assert run_debug_enabled(app) is True
    assert app.config["AI_RATE_LIMIT_WINDOW_SECONDS"] == 60
    assert app.config["AI_RATE_LIMIT_ANON_MAX"] == 10
    assert app.config["AI_RATE_LIMIT_USER_MAX"] == 20
    assert database_path(app) == Path(BASE_DIR) / "robot_shop.db"
    assert engine_database_path(app) == Path(BASE_DIR) / "robot_shop.db"
    assert configured_database_path() == Path(BASE_DIR) / "robot_shop.db"


def test_relative_sqlite_database_url_resolves_from_project_root(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/custom.db")

    app = create_app()

    assert database_path(app) == Path(BASE_DIR) / "data" / "custom.db"
    assert engine_database_path(app) == Path(BASE_DIR) / "data" / "custom.db"
    assert configured_database_path() == Path(BASE_DIR) / "data" / "custom.db"


def test_absolute_database_url_override_is_preserved(monkeypatch, tmp_path):
    custom_database = tmp_path / "custom.db"
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{custom_database}")

    app = create_app()

    assert database_path(app) == custom_database
    assert engine_database_path(app) == custom_database
    assert configured_database_path() == custom_database


def test_testing_config_can_create_app_without_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    app = create_app()

    assert app.config["TESTING"] is True


def test_production_config_requires_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        create_app()


def test_production_config_can_create_app_with_secret_key(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "production-secret-key")

    app = create_app()

    assert app.config["SECRET_KEY"] == "production-secret-key"
    assert app.config["DEBUG"] is False
    assert run_debug_enabled(app) is False
