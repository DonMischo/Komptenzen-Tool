"""test_deps.py — unit tests for JWT helpers and auth dependencies in deps.py."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from jose import jwt

import deps
from deps import (
    JWT_ALG,
    JWT_SECRET,
    _decode_token,
    create_token,
    get_current_admin,
    get_current_user,
    optional_user,
    optional_user_role,
)


# ---------------------------------------------------------------------------
# create_token / _decode_token
# ---------------------------------------------------------------------------

class TestCreateToken:
    def test_returns_string(self):
        token = create_token("alice")
        assert isinstance(token, str)

    def test_payload_sub(self):
        token = create_token("alice")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        assert payload["sub"] == "alice"

    def test_default_role_is_admin(self):
        token = create_token("alice")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        assert payload["role"] == "admin"

    def test_custom_role(self):
        token = create_token("bob", role="lehrer")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        assert payload["role"] == "lehrer"

    def test_expiry_in_future(self):
        token = create_token("alice")
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp > datetime.now(timezone.utc)


class TestDecodeToken:
    def test_valid_token(self):
        token = create_token("alice", role="admin")
        result = _decode_token(token)
        assert result == ("alice", "admin")

    def test_invalid_token(self):
        assert _decode_token("not.a.token") is None

    def test_expired_token(self):
        expire = datetime.now(timezone.utc) - timedelta(seconds=1)
        token = jwt.encode(
            {"sub": "alice", "role": "admin", "exp": expire},
            JWT_SECRET,
            algorithm=JWT_ALG,
        )
        assert _decode_token(token) is None

    def test_missing_sub(self):
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        token = jwt.encode(
            {"role": "admin", "exp": expire},
            JWT_SECRET,
            algorithm=JWT_ALG,
        )
        assert _decode_token(token) is None

    def test_wrong_secret(self):
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
        token = jwt.encode(
            {"sub": "alice", "role": "admin", "exp": expire},
            "wrong-secret",
            algorithm=JWT_ALG,
        )
        assert _decode_token(token) is None


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    def test_no_cookie_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            get_current_user(access_token=None)
        assert exc.value.status_code == 401

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            get_current_user(access_token="garbage")
        assert exc.value.status_code == 401

    def test_valid_token_returns_username(self):
        token = create_token("alice")
        result = get_current_user(access_token=token)
        assert result == "alice"

    def test_lehrer_token_accepted(self):
        token = create_token("bob", role="lehrer")
        result = get_current_user(access_token=token)
        assert result == "bob"


# ---------------------------------------------------------------------------
# get_current_admin
# ---------------------------------------------------------------------------

class TestGetCurrentAdmin:
    def test_no_cookie_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            get_current_admin(access_token=None)
        assert exc.value.status_code == 401

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc:
            get_current_admin(access_token="garbage")
        assert exc.value.status_code == 401

    def test_lehrer_role_raises_403(self):
        token = create_token("bob", role="lehrer")
        with pytest.raises(HTTPException) as exc:
            get_current_admin(access_token=token)
        assert exc.value.status_code == 403

    def test_admin_role_accepted(self):
        token = create_token("alice", role="admin")
        result = get_current_admin(access_token=token)
        assert result == "alice"


# ---------------------------------------------------------------------------
# optional_user / optional_user_role
# ---------------------------------------------------------------------------

class TestOptionalUser:
    def test_none_returns_none(self):
        assert optional_user(access_token=None) is None

    def test_invalid_token_returns_none(self):
        assert optional_user(access_token="bad") is None

    def test_valid_token_returns_username(self):
        token = create_token("alice")
        assert optional_user(access_token=token) == "alice"


class TestOptionalUserRole:
    def test_none_returns_none(self):
        assert optional_user_role(access_token=None) is None

    def test_valid_token_returns_tuple(self):
        token = create_token("alice", role="admin")
        result = optional_user_role(access_token=token)
        assert result == ("alice", "admin")
