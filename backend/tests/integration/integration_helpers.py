"""Shared constants and marks for integration tests."""
from __future__ import annotations

import os
import pytest
from sqlalchemy import create_engine

PG_BASE     = os.environ.get("POSTGRES_URL", "postgresql://appuser:Zeugnisdude@db:5432").rstrip("/")
POSTGRES_URL = f"{PG_BASE}/postgres"
REAL_DB_URL  = f"{PG_BASE}/reports_2025_26_ej"
TEST_DB      = "reports_inttest_tmp"
TEST_DB_URL  = f"{PG_BASE}/{TEST_DB}"


def _pg_reachable() -> bool:
    try:
        eng = create_engine(POSTGRES_URL, connect_args={"connect_timeout": 3})
        with eng.connect():
            pass
        eng.dispose()
        return True
    except Exception:
        return False


requires_pg = pytest.mark.skipif(not _pg_reachable(), reason="PostgreSQL not reachable")
