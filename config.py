import os

from sqlalchemy.engine import make_url

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
if load_dotenv:
    load_dotenv(os.path.join(BASE_DIR, ".env"))


def _normalize_database_url(database_url):
    url = make_url(database_url)
    if (
        url.drivername in {"sqlite", "sqlite+pysqlite"}
        and url.database not in {None, "", ":memory:"}
        and not os.path.isabs(url.database)
    ):
        url = url.set(database=os.path.abspath(os.path.join(BASE_DIR, url.database)))
    return url.render_as_string(hide_password=False)


def _database_url(default_name="robot_shop.db"):
    configured_url = os.environ.get("DATABASE_URL", "").strip()
    if configured_url:
        return _normalize_database_url(configured_url)
    return _normalize_database_url("sqlite:///" + os.path.join(BASE_DIR, default_name))


def _test_database_url():
    configured_url = os.environ.get("TEST_DATABASE_URL", "").strip()
    return _normalize_database_url(configured_url) if configured_url else "sqlite:///:memory:"


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "robot-shop-dev-secret-key")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    AI_RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("AI_RATE_LIMIT_WINDOW_SECONDS", 60))
    AI_RATE_LIMIT_ANON_MAX = int(os.environ.get("AI_RATE_LIMIT_ANON_MAX", 10))
    AI_RATE_LIMIT_USER_MAX = int(os.environ.get("AI_RATE_LIMIT_USER_MAX", 20))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    ENV = "development"


class TestingConfig(BaseConfig):
    TESTING = True
    ENV = "testing"
    SQLALCHEMY_DATABASE_URI = _test_database_url()


class ProductionConfig(BaseConfig):
    DEBUG = False
    ENV = "production"
    SECRET_KEY = os.environ.get("SECRET_KEY")


def get_config(config_name=None):
    config_name = (config_name or os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV") or "development").lower()
    config_map = {
        "development": DevelopmentConfig,
        "dev": DevelopmentConfig,
        "testing": TestingConfig,
        "test": TestingConfig,
        "production": ProductionConfig,
        "prod": ProductionConfig,
    }
    selected_config = config_map.get(config_name, DevelopmentConfig)
    if config_name in {"production", "prod"}:
        secret_key = os.environ.get("SECRET_KEY", "").strip()
        if not secret_key:
            raise RuntimeError("SECRET_KEY must be set when using ProductionConfig.")
        ProductionConfig.SECRET_KEY = secret_key
    selected_config.SQLALCHEMY_DATABASE_URI = (
        _test_database_url() if selected_config is TestingConfig else _database_url()
    )
    return selected_config


Config = DevelopmentConfig
