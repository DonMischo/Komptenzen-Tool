"""test_auth_pure.py — unit tests for auth_pure.py.

All tests swap out the module-level _auth_engine with a SQLite StaticPool
engine and stub _ensure_table (which contains Postgres-specific DDL) with a
plain create_all call.

Covers:
- user_count (total and role-filtered)
- create_user (admin and lehrer roles)
- list_users (ordering, structure)
- delete_user (existing, missing)
- get_role (existing user, unknown username)
- check_credentials (correct, wrong password, unknown user)
"""
from __future__ import annotations

from unittest.mock import patch

import bcrypt
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import auth_pure
from auth_pure import (
    AuthBase,
    AdminUser,
    user_count,
    create_user,
    list_users,
    delete_user,
    get_role,
    check_credentials,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def auth_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    AuthBase.metadata.create_all(eng)
    return eng


@pytest.fixture(autouse=True)
def patch_auth(auth_engine):
    """Replace module-level _auth_engine and stub _ensure_table for every test."""
    def _noop_ensure():
        AuthBase.metadata.create_all(auth_engine)

    with (
        patch.object(auth_pure, "_auth_engine", auth_engine),
        patch.object(auth_pure, "_ensure_table", side_effect=_noop_ensure),
    ):
        yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add_user(auth_engine, username: str, password: str, role: str = "admin"):
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with Session(auth_engine) as ses:
        ses.add(AdminUser(username=username, password_hash=hashed, role=role))
        ses.commit()


# ---------------------------------------------------------------------------
# user_count
# ---------------------------------------------------------------------------

class TestUserCount:
    def test_empty_db_returns_zero(self):
        assert user_count() == 0

    def test_counts_all_users(self, auth_engine):
        _add_user(auth_engine, "alice", "pw1", "admin")
        _add_user(auth_engine, "bob", "pw2", "lehrer")
        assert user_count() == 2

    def test_counts_by_role_admin(self, auth_engine):
        _add_user(auth_engine, "alice", "pw1", "admin")
        _add_user(auth_engine, "bob", "pw2", "lehrer")
        assert user_count(role="admin") == 1

    def test_counts_by_role_lehrer(self, auth_engine):
        _add_user(auth_engine, "alice", "pw1", "admin")
        _add_user(auth_engine, "bob", "pw2", "lehrer")
        assert user_count(role="lehrer") == 1

    def test_unknown_role_returns_zero(self, auth_engine):
        _add_user(auth_engine, "alice", "pw1", "admin")
        assert user_count(role="nonexistent") == 0


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

class TestCreateUser:
    def test_creates_admin_by_default(self, auth_engine):
        create_user("admin1", "secret")
        with Session(auth_engine) as ses:
            user = ses.query(AdminUser).filter_by(username="admin1").first()
        assert user is not None
        assert user.role == "admin"

    def test_creates_lehrer_role(self, auth_engine):
        create_user("teacher1", "secret", role="lehrer")
        with Session(auth_engine) as ses:
            user = ses.query(AdminUser).filter_by(username="teacher1").first()
        assert user.role == "lehrer"

    def test_password_is_hashed(self, auth_engine):
        create_user("admin2", "secret123")
        with Session(auth_engine) as ses:
            user = ses.query(AdminUser).filter_by(username="admin2").first()
        assert user.password_hash != "secret123"
        assert bcrypt.checkpw("secret123".encode(), user.password_hash.encode())

    def test_increments_count(self):
        assert user_count() == 0
        create_user("u1", "pw")
        assert user_count() == 1

    def test_multiple_users_stored(self):
        create_user("u1", "pw1")
        create_user("u2", "pw2")
        assert user_count() == 2


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------

class TestListUsers:
    def test_empty_returns_empty_list(self):
        assert list_users() == []

    def test_returns_list_of_dicts(self, auth_engine):
        _add_user(auth_engine, "alice", "pw", "admin")
        users = list_users()
        assert isinstance(users, list)
        assert isinstance(users[0], dict)

    def test_dict_has_required_keys(self, auth_engine):
        _add_user(auth_engine, "alice", "pw", "admin")
        user = list_users()[0]
        assert "id" in user
        assert "username" in user
        assert "role" in user

    def test_ordered_alphabetically(self, auth_engine):
        _add_user(auth_engine, "zorro", "pw", "admin")
        _add_user(auth_engine, "alice", "pw", "lehrer")
        names = [u["username"] for u in list_users()]
        assert names == sorted(names)

    def test_password_not_exposed(self, auth_engine):
        _add_user(auth_engine, "alice", "secret", "admin")
        user = list_users()[0]
        assert "password_hash" not in user
        assert "password" not in user

    def test_role_reflected(self, auth_engine):
        _add_user(auth_engine, "alice", "pw", "lehrer")
        user = list_users()[0]
        assert user["role"] == "lehrer"


# ---------------------------------------------------------------------------
# delete_user
# ---------------------------------------------------------------------------

class TestDeleteUser:
    def test_deletes_existing_user(self, auth_engine):
        _add_user(auth_engine, "alice", "pw")
        assert delete_user("alice") is True
        assert user_count() == 0

    def test_returns_false_for_unknown_user(self):
        assert delete_user("nobody") is False

    def test_only_deletes_named_user(self, auth_engine):
        _add_user(auth_engine, "alice", "pw")
        _add_user(auth_engine, "bob", "pw")
        delete_user("alice")
        assert user_count() == 1
        assert list_users()[0]["username"] == "bob"


# ---------------------------------------------------------------------------
# get_role
# ---------------------------------------------------------------------------

class TestGetRole:
    def test_returns_admin_role(self, auth_engine):
        _add_user(auth_engine, "alice", "pw", "admin")
        assert get_role("alice") == "admin"

    def test_returns_lehrer_role(self, auth_engine):
        _add_user(auth_engine, "bob", "pw", "lehrer")
        assert get_role("bob") == "lehrer"

    def test_returns_user_for_unknown(self):
        assert get_role("nobody") == "user"


# ---------------------------------------------------------------------------
# check_credentials
# ---------------------------------------------------------------------------

class TestCheckCredentials:
    def test_correct_password_returns_true(self, auth_engine):
        _add_user(auth_engine, "alice", "correct_pw")
        assert check_credentials("alice", "correct_pw") is True

    def test_wrong_password_returns_false(self, auth_engine):
        _add_user(auth_engine, "alice", "correct_pw")
        assert check_credentials("alice", "wrong_pw") is False

    def test_unknown_user_returns_false(self):
        assert check_credentials("nobody", "pw") is False

    def test_empty_password_returns_false(self, auth_engine):
        _add_user(auth_engine, "alice", "correct_pw")
        assert check_credentials("alice", "") is False

    def test_case_sensitive_username(self, auth_engine):
        _add_user(auth_engine, "Alice", "pw")
        assert check_credentials("alice", "pw") is False

    def test_different_users_checked_independently(self, auth_engine):
        _add_user(auth_engine, "alice", "pw_alice")
        _add_user(auth_engine, "bob", "pw_bob")
        assert check_credentials("alice", "pw_alice") is True
        assert check_credentials("bob", "pw_alice") is False
        assert check_credentials("alice", "pw_bob") is False
