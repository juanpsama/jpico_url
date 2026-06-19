import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.db import get_db_session, set_engine
from app.services.click_event_batcher import ClickEventBatcher, get_click_batcher
from app.services.click_event_service import ClickEventService, get_click_event_service
from app.services.refresh_token_service import RefreshTokenService, get_refresh_token_service
from app.services.url_map_service import UrlMapService, get_redirect_service, get_url_map_service
from app.services.user_service import UserService, get_user_service

SQLITE_URL = "sqlite://"

@pytest.fixture(name="engine", scope="function")
def engine_fixture():
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session", scope="function")
def session_fixture(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture(name="click_batcher", scope="function")
def click_batcher_fixture(engine):
    return ClickEventBatcher(engine, flush_interval=9999, batch_size=500)


@pytest.fixture(name="client", scope="function")
def client_fixture(session: Session, engine, click_batcher):
    refresh_token_service = RefreshTokenService(session)

    def override_get_db_session():
        yield session

    def override_get_refresh_token_service():
        return refresh_token_service

    def override_get_user_service():
        return UserService(session, refresh_token_service)

    def override_get_redirect_service():
        return UrlMapService(session, None)

    def override_get_url_map_service():
        return UrlMapService(session, None)

    def override_get_click_event_service():
        return ClickEventService(session)

    def override_get_click_batcher():
        return click_batcher

    set_engine(engine)

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_refresh_token_service] = override_get_refresh_token_service
    app.dependency_overrides[get_user_service] = override_get_user_service
    app.dependency_overrides[get_redirect_service] = override_get_redirect_service
    app.dependency_overrides[get_url_map_service] = override_get_url_map_service
    app.dependency_overrides[get_click_event_service] = override_get_click_event_service
    app.dependency_overrides[get_click_batcher] = override_get_click_batcher
    with TestClient(app, follow_redirects=False) as client:
        yield client
    app.dependency_overrides.clear()
