"""test_api_auth.py — HTTP-layer tests for routers/auth.py.

auth_pure functions are mocked so these tests only verify routing logic,
input validation, cookie handling, and response shapes.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# GET /api/auth/status
# ---------------------------------------------------------------------------

class TestAuthStatus:
    def test_returns_200(self, client):
        with patch("auth_pure.user_count", return_value=1):
            r = client.get("/api/auth/status")
        assert r.status_code == 200

    def test_needs_setup_true_when_no_users(self, client):
        with patch("auth_pure.user_count", return_value=0):
            r = client.get("/api/auth/status")
        assert r.json()["needs_setup"] is True

    def test_needs_setup_false_when_users_exist(self, client):
        with patch("auth_pure.user_count", return_value=1):
            r = client.get("/api/auth/status")
        assert r.json()["needs_setup"] is False

    def test_authenticated_always_false(self, client):
        with patch("auth_pure.user_count", return_value=1):
            r = client.get("/api/auth/status")
        assert r.json()["authenticated"] is False

    def test_username_always_null(self, client):
        with patch("auth_pure.user_count", return_value=1):
            r = client.get("/api/auth/status")
        assert r.json()["username"] is None


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------

class TestAuthMe:
    def test_returns_200(self, client):
        with patch("auth_pure.user_count", return_value=1):
            r = client.get("/api/auth/me")
        assert r.status_code == 200

    def test_authenticated_false_without_token(self, client):
        with patch("auth_pure.user_count", return_value=1):
            r = client.get("/api/auth/me")
        assert r.json()["authenticated"] is False

    def test_authenticated_true_with_valid_cookie(self, client):
        from deps import create_token
        token = create_token("alice", "admin")
        with patch("auth_pure.user_count", return_value=1):
            r = client.get("/api/auth/me", cookies={"access_token": token})
        assert r.json()["authenticated"] is True
        assert r.json()["username"] == "alice"


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_valid_credentials_returns_200(self, client):
        with (
            patch("auth_pure.check_credentials", return_value=True),
            patch("auth_pure.get_role", return_value="admin"),
        ):
            r = client.post("/api/auth/login", json={"username": "alice", "password": "secret"})
        assert r.status_code == 200

    def test_returns_username_and_role(self, client):
        with (
            patch("auth_pure.check_credentials", return_value=True),
            patch("auth_pure.get_role", return_value="lehrer"),
        ):
            r = client.post("/api/auth/login", json={"username": "bob", "password": "pw"})
        assert r.json()["username"] == "bob"
        assert r.json()["role"] == "lehrer"

    def test_sets_cookie(self, client):
        with (
            patch("auth_pure.check_credentials", return_value=True),
            patch("auth_pure.get_role", return_value="admin"),
        ):
            r = client.post("/api/auth/login", json={"username": "alice", "password": "secret"})
        assert "access_token" in r.cookies

    def test_wrong_credentials_returns_401(self, client):
        with patch("auth_pure.check_credentials", return_value=False):
            r = client.post("/api/auth/login", json={"username": "alice", "password": "wrong"})
        assert r.status_code == 401

    def test_ok_field_true_on_success(self, client):
        with (
            patch("auth_pure.check_credentials", return_value=True),
            patch("auth_pure.get_role", return_value="admin"),
        ):
            r = client.post("/api/auth/login", json={"username": "alice", "password": "pw"})
        assert r.json()["ok"] is True


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_returns_200(self, client):
        r = client.post("/api/auth/logout")
        assert r.status_code == 200

    def test_returns_ok(self, client):
        r = client.post("/api/auth/logout")
        assert r.json()["ok"] is True

    def test_deletes_cookie(self, client):
        from deps import create_token
        token = create_token("alice", "admin")
        r = client.post("/api/auth/logout", cookies={"access_token": token})
        # Cookie should be cleared (max-age=0 or deleted)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# POST /api/auth/setup
# ---------------------------------------------------------------------------

class TestSetup:
    def test_creates_first_admin(self, client):
        with (
            patch("auth_pure.user_count", return_value=0),
            patch("auth_pure.create_user") as mock_create,
        ):
            r = client.post("/api/auth/setup", json={"username": "admin", "password": "securepass"})
        assert r.status_code == 200
        mock_create.assert_called_once_with("admin", "securepass", role="admin")

    def test_returns_authenticated_true(self, client):
        with (
            patch("auth_pure.user_count", return_value=0),
            patch("auth_pure.create_user"),
        ):
            r = client.post("/api/auth/setup", json={"username": "admin", "password": "securepass"})
        assert r.json()["authenticated"] is True
        assert r.json()["needs_setup"] is False

    def test_sets_cookie_on_setup(self, client):
        with (
            patch("auth_pure.user_count", return_value=0),
            patch("auth_pure.create_user"),
        ):
            r = client.post("/api/auth/setup", json={"username": "admin", "password": "securepass"})
        assert "access_token" in r.cookies

    def test_already_setup_returns_400(self, client):
        with patch("auth_pure.user_count", return_value=1):
            r = client.post("/api/auth/setup", json={"username": "admin", "password": "securepass"})
        assert r.status_code == 400

    def test_short_password_returns_400(self, client):
        with patch("auth_pure.user_count", return_value=0):
            r = client.post("/api/auth/setup", json={"username": "admin", "password": "short"})
        assert r.status_code == 400

    def test_empty_username_returns_400(self, client):
        with patch("auth_pure.user_count", return_value=0):
            r = client.post("/api/auth/setup", json={"username": "", "password": "securepass"})
        assert r.status_code == 400


# ---------------------------------------------------------------------------
# POST /api/auth/users
# ---------------------------------------------------------------------------

class TestCreateUserEndpoint:
    def test_creates_user(self, client):
        with patch("auth_pure.create_user") as mock_create:
            r = client.post(
                "/api/auth/users",
                json={"username": "teacher1", "password": "pass123", "role": "lehrer"},
            )
        assert r.status_code == 200
        mock_create.assert_called_once()

    def test_returns_username_and_role(self, client):
        with patch("auth_pure.create_user"):
            r = client.post(
                "/api/auth/users",
                json={"username": "teacher1", "password": "pass123", "role": "lehrer"},
            )
        assert r.json()["username"] == "teacher1"
        assert r.json()["role"] == "lehrer"

    def test_short_password_returns_400(self, client):
        r = client.post(
            "/api/auth/users",
            json={"username": "teacher1", "password": "pw", "role": "lehrer"},
        )
        assert r.status_code == 400

    def test_invalid_role_returns_400(self, client):
        r = client.post(
            "/api/auth/users",
            json={"username": "teacher1", "password": "password", "role": "superuser"},
        )
        assert r.status_code == 400

    def test_duplicate_user_returns_409(self, client):
        from sqlalchemy.exc import IntegrityError
        with patch("auth_pure.create_user", side_effect=IntegrityError("", "", None)):
            r = client.post(
                "/api/auth/users",
                json={"username": "dup", "password": "password", "role": "admin"},
            )
        assert r.status_code == 409
