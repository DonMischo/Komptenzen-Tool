"""Integration tests for auth_pure.py against real PostgreSQL."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from integration_helpers import requires_pg, POSTGRES_URL
import auth_pure
from auth_pure import AuthBase, AdminUser


@pytest.fixture(autouse=True)
def _use_real_engine():
    """Point _auth_engine at real postgres for every test in this module."""
    real_eng = create_engine(POSTGRES_URL, future=True)
    original = auth_pure._auth_engine
    auth_pure._auth_engine = real_eng
    auth_pure._ensure_table()
    yield
    auth_pure._auth_engine = original
    real_eng.dispose()


@pytest.fixture(autouse=True)
def _cleanup():
    """Delete any test user created during the test."""
    yield
    auth_pure.delete_user("inttest_user")


@requires_pg
class TestAuthPureIntegration:
    def test_create_user_and_verify(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        assert auth_pure.check_credentials("inttest_user", "Secure1234!") is True

    def test_wrong_password_rejected(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        assert auth_pure.check_credentials("inttest_user", "wrongpw") is False

    def test_unknown_user_rejected(self):
        assert auth_pure.check_credentials("nobody_int", "pw") is False

    def test_get_role_lehrer(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        assert auth_pure.get_role("inttest_user") == "lehrer"

    def test_get_role_admin(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="admin")
        assert auth_pure.get_role("inttest_user") == "admin"

    def test_get_role_unknown_returns_user(self):
        assert auth_pure.get_role("nobody_int") == "user"

    def test_list_users_contains_created(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        usernames = [u["username"] for u in auth_pure.list_users()]
        assert "inttest_user" in usernames

    def test_list_users_excludes_deleted(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        auth_pure.delete_user("inttest_user")
        usernames = [u["username"] for u in auth_pure.list_users()]
        assert "inttest_user" not in usernames

    def test_delete_returns_true(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        assert auth_pure.delete_user("inttest_user") is True

    def test_delete_nonexistent_returns_false(self):
        assert auth_pure.delete_user("nobody_int") is False

    def test_user_count_increases(self):
        before = auth_pure.user_count()
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        assert auth_pure.user_count() == before + 1

    def test_user_count_by_role(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        count = auth_pure.user_count(role="lehrer")
        assert count >= 1

    def test_password_not_stored_in_plaintext(self):
        auth_pure.create_user("inttest_user", "Secure1234!", role="lehrer")
        real_eng = create_engine(POSTGRES_URL, future=True)
        with Session(real_eng) as ses:
            user = ses.query(AdminUser).filter_by(username="inttest_user").first()
            assert user is not None
            assert user.password_hash != "Secure1234!"
        real_eng.dispose()
