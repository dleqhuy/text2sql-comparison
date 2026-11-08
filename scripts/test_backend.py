"""Run backend tests only against a separate PostgreSQL *_test database."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.core.config import settings

base = urlsplit(
    str(settings.DATABASE_URL).replace("postgresql+psycopg://", "postgresql://")
)
url = os.environ.get(
    "TEST_DATABASE_URL", urlunsplit(base._replace(path=base.path + "_test"))
)
parts = urlsplit(url)
name = parts.path.lstrip("/")
if not name.endswith("_test"):
    raise SystemExit("TEST_DATABASE_URL must point to a dedicated *_test database")
try:
    with psycopg.connect(
        urlunsplit(parts._replace(path="/postgres")), autocommit=True
    ) as conn:
        if not conn.execute(
            "SELECT 1 FROM pg_database WHERE datname=%s", [name]
        ).fetchone():
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
except psycopg.OperationalError:
    raise SystemExit(
        "PostgreSQL is unavailable. Start npm run dev (or your PostgreSQL service) first."
    )
with tempfile.TemporaryDirectory(prefix="sql-lab-test-runs-") as directory:
    env = {
        **os.environ,
        "DATABASE_URL": url,
        "SQL_LAB_IMPORT_LEGACY": "0",
        "SQL_LAB_RUNS_DIR": directory,
    }
    python = ROOT / "backend/.venv/bin/python"
    result = subprocess.run(
        [str(python), "-m", "alembic", "upgrade", "head"],
        cwd=ROOT / "backend",
        env=env,
        check=False,
    )
    if result.returncode:
        raise SystemExit(result.returncode)
    result = subprocess.run(
        [str(python), "-m", "pytest", "tests", "-q", *sys.argv[1:]],
        cwd=ROOT / "backend",
        env=env,
        check=False,
    )
    raise SystemExit(result.returncode)
