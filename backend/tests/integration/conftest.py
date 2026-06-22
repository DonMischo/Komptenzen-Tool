"""conftest.py for integration tests — no psycopg2 stub."""
from __future__ import annotations

import os
import sys

_BACKEND = "/backend"
_INT_DIR = os.path.join(_BACKEND, "tests", "integration")
for _p in (_BACKEND, _INT_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest
from sqlalchemy import create_engine, text

from integration_helpers import PG_BASE, POSTGRES_URL, TEST_DB, TEST_DB_URL


@pytest.fixture(scope="module")
def pg_admin():
    eng = create_engine(POSTGRES_URL, isolation_level="AUTOCOMMIT")
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def test_db(pg_admin):
    with pg_admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    yield TEST_DB_URL
    with pg_admin.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB}"))


@pytest.fixture(scope="module")
def test_db_engine(test_db):
    eng = create_engine(test_db, future=True)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def real_db_engine():
    from integration_helpers import REAL_DB_URL
    eng = create_engine(REAL_DB_URL, future=True)
    yield eng
    eng.dispose()
