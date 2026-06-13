import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.db import get_db_session
from app.services.url_map_service import UrlMapService, get_redirect_service

# Use an in-memory SQLite database for tests.
# StaticPool ensures the same in-memory database connection is reused
# across all threads during the test session (required by TestClient).
SQLITE_URL = "sqlite://"

@pytest.fixture(name="session", scope="function")
def session_fixture():
    """
    Creates a fresh in-memory SQLite database and all tables for each
    individual test function, then drops everything after the test completes.
    This guarantees full isolation between tests.
    """
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client", scope="function")
def client_fixture(session: Session):
    """
    Provides a FastAPI TestClient that uses the test database session
    instead of the real PostgreSQL session via dependency override.
    """
    def override_get_db_session():
        yield session

    def override_get_redirect_service():
        return UrlMapService(session, None)

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redirect_service] = override_get_redirect_service
    with TestClient(app, follow_redirects=False) as client:
        yield client
    app.dependency_overrides.clear()
