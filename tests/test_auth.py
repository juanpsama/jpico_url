from fastapi.testclient import TestClient
from sqlmodel import Session

REGISTER_PAYLOAD = {
    "username": "testuser",
    "email": "test@example.com",
    "password": "supersecret123",
}

LOGIN_DATA = {
    "username": "testuser",
    "password": "supersecret123",
}

LOGIN_BAD_PW = {
    "username": "testuser",
    "password": "wrongpassword",
}


def _register(client: TestClient) -> dict:
    response = client.post("/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 200
    return response.json()


class TestRegister:
    def test_register_returns_tokens(self, client: TestClient, session: Session):
        data = _register(client)
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_register_duplicate_username_409(self, client: TestClient, session: Session):
        _register(client)
        r = client.post("/auth/register", json={
            "username": "testuser",
            "email": "other@example.com",
            "password": "supersecret123",
        })
        assert r.status_code == 409
        assert r.json()["detail"] == "Username already taken"

    def test_register_duplicate_email_409(self, client: TestClient, session: Session):
        _register(client)
        r = client.post("/auth/register", json={
            "username": "otheruser",
            "email": "test@example.com",
            "password": "supersecret123",
        })
        assert r.status_code == 409
        assert r.json()["detail"] == "Email already registered"


class TestLogin:
    def test_login_returns_tokens(self, client: TestClient, session: Session):
        _register(client)
        r = client.post("/auth/login", data=LOGIN_DATA)
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_credentials_401(self, client: TestClient, session: Session):
        _register(client)
        r = client.post("/auth/login", data=LOGIN_BAD_PW)
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid credentials"


class TestRefresh:
    def test_refresh_returns_new_tokens(self, client: TestClient, session: Session):
        tokens = _register(client)
        r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] != tokens["refresh_token"]

    def test_old_refresh_token_revoked_after_rotation(self, client: TestClient, session: Session):
        tokens = _register(client)
        old_refresh = tokens["refresh_token"]
        r = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert r.status_code == 200
        r2 = client.post("/auth/refresh", json={"refresh_token": old_refresh})
        assert r2.status_code == 401
        assert r2.json()["detail"] == "Token has been revoked"

    def test_refresh_invalid_token_returns_401(self, client: TestClient, session: Session):
        _register(client)
        r = client.post("/auth/refresh", json={"refresh_token": "invalidtoken"})
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid token"

    def test_refresh_with_access_token_returns_401(self, client: TestClient, session: Session):
        tokens = _register(client)
        r = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["access_token"]},
        )
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid token type"

    def test_refreshed_access_token_works_on_me(self, client: TestClient, session: Session):
        tokens = _register(client)
        r1 = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
        assert r1.status_code == 200
        new_tokens = r1.json()
        r2 = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
        )
        assert r2.status_code == 200
        assert r2.json()["username"] == "testuser"


class TestMe:
    def test_me_returns_user(self, client: TestClient, session: Session):
        tokens = _register(client)
        r = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
        assert r.status_code == 200
        data = r.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"

    def test_me_unauthorized_without_token(self, client: TestClient, session: Session):
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_me_unauthorized_with_invalid_token(self, client: TestClient, session: Session):
        r = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code == 401

    def test_me_unauthorized_with_expired_token_style(self, client: TestClient, session: Session):
        r = client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert r.status_code == 401
