from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED_MODULES = {
    "flask": "Flask",
    "flask_login": "Flask-Login",
    "flask_sqlalchemy": "Flask-SQLAlchemy",
    "sqlalchemy": "SQLAlchemy",
    "dotenv": "python-dotenv",
}


def ok(message: str) -> None:
    print(f"[OK] {message}")


def warn(message: str) -> None:
    print(f"[WARN] {message}")


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def check_python_version() -> bool:
    version = sys.version_info
    version_text = f"{version.major}.{version.minor}.{version.micro}"
    if version >= (3, 10):
        ok(f"Python version: {version_text}")
        return True
    fail(f"Python 3.10+ is recommended. Current version: {version_text}")
    return False


def check_dependencies() -> bool:
    missing = []
    for module_name, package_name in REQUIRED_MODULES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package_name)

    if missing:
        fail("Missing dependencies: " + ", ".join(missing))
        print("      Run: pip install -r requirements.txt")
        return False

    ok("Required runtime dependencies are installed")
    return True


def check_file(path: Path, label: str, required: bool = True) -> bool:
    if path.exists():
        ok(f"{label} exists: {path.name}")
        return True

    if required:
        fail(f"{label} is missing: {path.name}")
        return False

    warn(f"{label} is missing: {path.name}")
    return True


def configured_database_path() -> Path | None:
    from sqlalchemy.engine import make_url

    from config import _database_url

    url = make_url(_database_url())
    if url.drivername not in {"sqlite", "sqlite+pysqlite"}:
        return None
    if url.database in {None, "", ":memory:"}:
        return None
    return Path(url.database)


def check_database() -> bool:
    try:
        database_path = configured_database_path()
    except ImportError:
        warn("Database file check skipped because SQLAlchemy is unavailable")
        return True

    if database_path is None:
        ok("Configured database does not use a file-based SQLite database")
        return True
    return check_file(database_path, "SQLite database file", required=False)


def main() -> int:
    print("Robot Shop local project check")
    print(f"Project root: {ROOT}")
    print()

    checks = [
        check_python_version(),
        check_dependencies(),
        check_file(ROOT / "app.py", "Application entry"),
        check_file(ROOT / ".env", "Local environment file", required=False),
        check_database(),
    ]

    print()
    if all(checks):
        ok("Project check completed")
        return 0

    fail("Project check found issues")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
