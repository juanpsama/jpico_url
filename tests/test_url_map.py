from datetime import datetime, UTC

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.url_map import UrlMap


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
