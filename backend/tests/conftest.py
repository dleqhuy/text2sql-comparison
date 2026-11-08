from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, delete

from app.core.config import settings
from app.core.db import engine
from app.live_models import PipelineRun
from app.main import app

if not (settings.DATABASE_URL.path or "").endswith("_test"):
    raise RuntimeError(
        "Refusing destructive tests outside a dedicated *_test database. Use npm run test:backend."
    )


@pytest.fixture(scope="session", autouse=True)
def db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
        session.exec(delete(PipelineRun))
        session.commit()


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as client:
        yield client
