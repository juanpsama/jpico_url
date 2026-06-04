from datetime import datetime, UTC

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.url_map import UrlMap


def _insert_url_map(session: Session, original_url: str, short_url_code: str) -> UrlMap:
    """Helper to insert a UrlMap record directly into the test database."""
    url_map = UrlMap(
        original_url=original_url,
        short_url_code=short_url_code,
        create_date=datetime.now(UTC),
    )
    session.add(url_map)
    session.commit()
    session.refresh(url_map)
    return url_map


class TestGetUrlMap:
    """Tests for the GET /{short_code} redirect route."""

    def test_redirect_returns_302(self, client: TestClient, session: Session):
        """
        A valid short code must return a 302 Found status code.
        """
        _insert_url_map(session, "https://google.com", "ab1c")

        response = client.get("/ab1c")

        assert response.status_code == 302

    def test_redirect_location_header_points_to_original_url(self, client: TestClient, session: Session):
        """
        The Location header must contain the exact original URL stored in the database.
        """
        _insert_url_map(session, "https://google.com", "ab1c")

        response = client.get("/ab1c")

        assert response.headers["location"] == "https://google.com"

    def test_redirect_not_found_returns_404(self, client: TestClient, session: Session):
        """
        A short code that does not exist in the database must return 404 Not Found.
        """
        response = client.get("/xxxx")

        assert response.status_code == 404

    def test_redirect_not_found_returns_detail_message(self, client: TestClient, session: Session):
        """
        A missing short code must return the expected error detail message.
        """
        response = client.get("/xxxx")

        assert response.json()["detail"] == "URL not found"

    def test_redirect_is_case_sensitive(self, client: TestClient, session: Session):
        """
        Short codes are case-sensitive. 'Ab1c' and 'ab1c' must be treated as different codes.
        """
        _insert_url_map(session, "https://google.com", "ab1c")

        response = client.get("/Ab1c")

        assert response.status_code == 404
