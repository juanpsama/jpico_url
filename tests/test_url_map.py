from datetime import datetime, UTC

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.click_event import ClickEvent
from app.models.url_map import UrlMap
from app.models.user import User


def _insert_url_map(session: Session, original_url: str, short_url_code: str, owner_id: int | None = None) -> UrlMap:
    url_map = UrlMap(
        original_url=original_url,
        short_url_code=short_url_code,
        create_date=datetime.now(UTC),
        owner_id=owner_id,
    )
    session.add(url_map)
    session.commit()
    session.refresh(url_map)
    return url_map


def _get_user_id(session: Session, username: str) -> int:
    user = session.exec(select(User).where(User.username == username)).first()
    return user.id


def _register_user(client: TestClient, username: str = "testuser") -> dict:
    r = client.post("/auth/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "supersecret123",
    })
    assert r.status_code == 200
    return r.json()


class TestGetUrlMap:
    def test_redirect_returns_302(self, client: TestClient, session: Session):
        _insert_url_map(session, "https://google.com", "ab1c")
        response = client.get("/ab1c")
        assert response.status_code == 302

    def test_redirect_location_header_points_to_original_url(self, client: TestClient, session: Session):
        _insert_url_map(session, "https://google.com", "ab1c")
        response = client.get("/ab1c")
        assert response.headers["location"] == "https://google.com"

    def test_redirect_not_found_returns_404(self, client: TestClient, session: Session):
        response = client.get("/xxxx")
        assert response.status_code == 404

    def test_redirect_not_found_returns_detail_message(self, client: TestClient, session: Session):
        response = client.get("/xxxx")
        assert response.json()["detail"] == "URL not found"

    def test_redirect_is_case_sensitive(self, client: TestClient, session: Session):
        _insert_url_map(session, "https://google.com", "ab1c")
        response = client.get("/Ab1c")
        assert response.status_code == 404


class TestShorten:
    def test_shorten_as_guest_no_owner(self, client: TestClient, session: Session):
        r = client.post("/shorten", json={"original_url": "https://example.com"})
        assert r.status_code == 200
        data = r.json()
        assert data["owner_id"] is None

    def test_shorten_authenticated_sets_owner(self, client: TestClient, session: Session):
        tokens = _register_user(client)
        r = client.post(
            "/shorten",
            json={"original_url": "https://example.com"},
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["owner_id"] is not None


class TestMyUrls:
    def test_my_urls_requires_auth(self, client: TestClient, session: Session):
        r = client.get("/my-urls")
        assert r.status_code == 401

    def test_my_urls_returns_only_owned(self, client: TestClient, session: Session):
        tokens_a = _register_user(client, "user_a")
        tokens_b = _register_user(client, "user_b")

        client.post(
            "/shorten",
            json={"original_url": "https://a.com"},
            headers={"Authorization": f"Bearer {tokens_a['access_token']}"},
        )
        client.post(
            "/shorten",
            json={"original_url": "https://b.com"},
            headers={"Authorization": f"Bearer {tokens_b['access_token']}"},
        )

        r = client.get("/my-urls", headers={"Authorization": f"Bearer {tokens_a['access_token']}"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 1
        assert data["data"][0]["original_url"] == "https://a.com"


class TestClickTracking:
    def test_click_recorded_on_redirect(self, client: TestClient, session: Session, click_batcher):
        url_map = _insert_url_map(session, "https://example.com", "abc1")
        client.get("/abc1")
        click_batcher.flush()
        clicks = session.exec(
            select(ClickEvent).where(ClickEvent.url_map_id == url_map.id)
        ).all()
        assert len(clicks) == 1

    def test_click_metadata_stored(self, client: TestClient, session: Session, click_batcher):
        url_map = _insert_url_map(session, "https://example.com", "abc2")
        client.get("/abc2", headers={"User-Agent": "test-agent", "Referer": "https://referer.com"})
        click_batcher.flush()
        click = session.exec(
            select(ClickEvent).where(ClickEvent.url_map_id == url_map.id)
        ).first()
        assert click is not None
        assert click.url_map_id == url_map.id
        assert click.user_agent == "test-agent"
        assert click.referer == "https://referer.com"
        assert click.clicked_at is not None

    def test_no_click_on_404(self, client: TestClient, session: Session):
        client.get("/nonexistent")
        total = session.exec(select(ClickEvent)).all()
        assert len(total) == 0

    def test_stats_requires_auth(self, client: TestClient, session: Session):
        _insert_url_map(session, "https://example.com", "abc3")
        r = client.get("/urls/abc3/stats")
        assert r.status_code == 401

    def test_stats_requires_ownership(self, client: TestClient, session: Session):
        tokens = _register_user(client, "owner")
        _insert_url_map(session, "https://example.com", "abc4", owner_id=999)
        r = client.get(
            "/urls/abc4/stats",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert r.status_code == 403

    def test_stats_returns_correct_count(self, client: TestClient, session: Session):
        tokens = _register_user(client, "owner")
        user_id = _get_user_id(session, "owner")
        url_map = _insert_url_map(session, "https://example.com", "abc5", owner_id=user_id)

        session.add(ClickEvent(url_map_id=url_map.id, ip_address="1.2.3.4"))
        session.add(ClickEvent(url_map_id=url_map.id, ip_address="5.6.7.8"))
        session.commit()

        r = client.get(
            "/urls/abc5/stats",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_clicks"] == 2
        assert data["url_map_id"] == url_map.id

    def test_clicks_pagination(self, client: TestClient, session: Session):
        tokens = _register_user(client, "owner")
        user_id = _get_user_id(session, "owner")
        url_map = _insert_url_map(session, "https://example.com", "abc6", owner_id=user_id)

        for i in range(5):
            session.add(ClickEvent(url_map_id=url_map.id, ip_address=f"1.2.3.{i}"))
        session.commit()

        r = client.get(
            "/urls/abc6/clicks?page=0&per_page=2",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 5
        assert data["per_page"] == 2
        assert len(data["data"]) == 2

    def test_export_returns_501(self, client: TestClient, session: Session):
        tokens = _register_user(client, "owner")
        user_id = _get_user_id(session, "owner")
        _insert_url_map(session, "https://example.com", "abc7", owner_id=user_id)
        r = client.get(
            "/urls/abc7/clicks/export",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert r.status_code == 501
