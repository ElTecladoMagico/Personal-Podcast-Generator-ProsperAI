import os

# Deterministic settings for tests; must run before `app` is imported.
os.environ |= {
    "DATABASE_URL": "postgresql+psycopg://podcast:podcast@localhost:5433/podcast_test",
    "CLERK_ISSUER": "https://test.clerk.example",
    "CLERK_AUTHORIZED_PARTIES": "http://localhost:5173",
    "CORS_ORIGINS": "http://localhost:5173",
    "SCHEDULER_ENABLED": "false",
}

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

import app.models  # noqa: E402, F401
from app.auth import get_claims  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def schema():
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clean_tables():
    yield
    with engine.begin() as conn:
        for table in reversed(SQLModel.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def claims() -> dict:
    """Claims of the signed-in test user; tests may mutate them before calling the API."""
    return {"sub": "user_123", "email": "ana@example.com", "name": "Ana"}


@pytest.fixture
def client(claims):
    fastapi_app.dependency_overrides[get_claims] = lambda: claims
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()
