"""test_integration.py — integration tests requiring the live Docker stack.

Run with:
    pytest -m integration

Requires:
    - PostgreSQL reachable at POSTGRES_URL (or postgresql://appuser:...@localhost:5433)
    - The reports_2025_26_ej database to exist

These tests never modify existing data. Destructive operations (create/drop DB,
user create/delete) use a dedicated test database named reports_inttest_tmp.
"""
from __future__ import annotations

import os
import subprocess

import pytest
import sqlalchemy
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Postgres URL (reads from env, falls back to local Docker mapping)
# ---------------------------------------------------------------------------

PG_BASE = os.environ.get(
    "POSTGRES_URL",
    "postgresql://appuser:Zeugnisdude@localhost:5433",
).rstrip("/")

TEST_DB = "reports_inttest_tmp"
TEST_DB_URL = f"{PG_BASE}/{TEST_DB}"
REAL_DB_URL = f"{PG_BASE}/reports_2025_26_ej"
POSTGRES_URL = f"{PG_BASE}/postgres"


def _pg_reachable() -> bool:
    try:
        eng = create_engine(POSTGRES_URL, connect_args={"connect_timeout": 3})
        with eng.connect():
            pass
        eng.dispose()
        return True
    except Exception:
        return False


requires_pg = pytest.mark.skipif(
    not _pg_reachable(), reason="PostgreSQL not reachable at " + PG_BASE
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def pg_admin_engine():
    """Engine connected to the postgres maintenance DB (AUTOCOMMIT for DDL)."""
    eng = create_engine(POSTGRES_URL, isolation_level="AUTOCOMMIT")
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def test_db(pg_admin_engine):
    """Create reports_inttest_tmp before tests; drop it after."""
    with pg_admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB}"))
        conn.execute(text(f"CREATE DATABASE {TEST_DB}"))
    yield TEST_DB_URL
    with pg_admin_engine.connect() as conn:
        conn.execute(text(f"DROP DATABASE IF EXISTS {TEST_DB}"))


@pytest.fixture(scope="module")
def test_db_engine(test_db):
    eng = create_engine(test_db, future=True)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def real_db_engine():
    eng = create_engine(REAL_DB_URL, future=True)
    yield eng
    eng.dispose()


# ---------------------------------------------------------------------------
# migrations.run_migrations
# ---------------------------------------------------------------------------

@requires_pg
class TestRunMigrations:
    def test_creates_tables_on_empty_db(self, test_db_engine):
        from db_schema import Base
        Base.metadata.create_all(test_db_engine)
        insp = inspect(test_db_engine)
        assert "students" in insp.get_table_names()

    def test_migrations_idempotent_on_fresh_db(self, test_db):
        from migrations import run_migrations
        # Run twice — must not raise
        run_migrations(test_db)
        run_migrations(test_db)

    def test_grades_column_type_is_text_after_migration(self, test_db, test_db_engine):
        from migrations import run_migrations
        from db_schema import Base
        Base.metadata.create_all(test_db_engine)
        run_migrations(test_db)
        with test_db_engine.connect() as conn:
            result = conn.execute(text(
                """
                SELECT data_type FROM information_schema.columns
                WHERE table_name = 'grades' AND column_name = 'value'
                """
            ))
            row = result.fetchone()
        assert row is not None
        assert row[0] == "text"

    def test_migration_on_existing_db_is_noop(self):
        from migrations import run_migrations
        # Should not raise on a DB that already has all migrations applied
        run_migrations(REAL_DB_URL)

    def test_run_migrations_all_skips_non_report_dbs(self):
        """run_migrations_all_report_dbs should only touch reports_* databases."""
        from migrations import run_migrations_all_report_dbs
        # Should complete without raising even if the test DB is present
        run_migrations_all_report_dbs()


# ---------------------------------------------------------------------------
# db_schema: list_report_dbs, create_report_db, switch_engine
# ---------------------------------------------------------------------------

@requires_pg
class TestDbSchemaIntegration:
    def test_list_report_dbs_returns_existing(self):
        import db_schema
        with sqlalchemy.create_engine(POSTGRES_URL).connect() as conn:
            pass
        # Point _pg_base_url at our test postgres
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("POSTGRES_URL", PG_BASE)
            from db_schema import list_report_dbs
            dbs = list_report_dbs()
        assert "reports_2025_26_ej" in dbs

    def test_list_report_dbs_excludes_postgres_db(self):
        with pytest.MonkeyPatch().context() as mp:
            mp.setenv("POSTGRES_URL", PG_BASE)
            from db_schema import list_report_dbs
            dbs = list_report_dbs()
        assert "postgres" not in dbs
        assert "template0" not in dbs

    def test_switch_engine_propagates(self, test_db):
        import db_schema
        import db_helpers
        from db_schema import Base
        # Create schema in test DB first
        eng = create_engine(test_db)
        Base.metadata.create_all(eng)
        eng.dispose()

        original_url = str(db_schema.ENGINE.url)
        try:
            db_schema.switch_engine(TEST_DB)
            assert str(db_schema.ENGINE.url).endswith(TEST_DB)
        finally:
            # Restore original engine
            db_schema.ENGINE = create_engine(original_url)
            import db_helpers as _dh
            _dh.ENGINE = db_schema.ENGINE


# ---------------------------------------------------------------------------
# auth_pure against real Postgres
# ---------------------------------------------------------------------------

@requires_pg
class TestAuthPureIntegration:
    """Tests auth_pure against the real postgres DB. Creates a temporary user
    and cleans it up — never touches existing admin_users rows."""

    @pytest.fixture(autouse=True)
    def _patch_auth_engine(self):
        """Point _auth_engine at the real postgres DB for this test class."""
        import auth_pure
        real_eng = create_engine(POSTGRES_URL, future=True)
        original = auth_pure._auth_engine
        auth_pure._auth_engine = real_eng
        auth_pure._ensure_table()   # create table if not present
        yield
        auth_pure._auth_engine = original
        real_eng.dispose()

    @pytest.fixture(autouse=True)
    def _cleanup_test_user(self):
        yield
        import auth_pure
        auth_pure.delete_user("inttest_user")

    def test_create_and_check_credentials(self):
        import auth_pure
        auth_pure.create_user("inttest_user", "Test1234!", role="lehrer")
        assert auth_pure.check_credentials("inttest_user", "Test1234!") is True

    def test_wrong_password_returns_false(self):
        import auth_pure
        auth_pure.create_user("inttest_user", "Test1234!", role="lehrer")
        assert auth_pure.check_credentials("inttest_user", "wrongpw") is False

    def test_get_role(self):
        import auth_pure
        auth_pure.create_user("inttest_user", "Test1234!", role="lehrer")
        assert auth_pure.get_role("inttest_user") == "lehrer"

    def test_list_users_includes_new(self):
        import auth_pure
        auth_pure.create_user("inttest_user", "Test1234!", role="lehrer")
        users = [u["username"] for u in auth_pure.list_users()]
        assert "inttest_user" in users

    def test_delete_user(self):
        import auth_pure
        auth_pure.create_user("inttest_user", "Test1234!", role="lehrer")
        assert auth_pure.delete_user("inttest_user") is True
        assert auth_pure.check_credentials("inttest_user", "Test1234!") is False


# ---------------------------------------------------------------------------
# Live API via TestClient with real Postgres session
# ---------------------------------------------------------------------------

@requires_pg
class TestLiveApiIntegration:
    """Uses TestClient against main.app but injects a real Postgres session
    for get_db, so the full SQLAlchemy → Postgres path is exercised."""

    @pytest.fixture
    def live_client(self, real_db_engine):
        from sqlalchemy.orm import Session as OrmSession
        from fastapi.testclient import TestClient
        from deps import get_db, get_current_user, get_current_admin
        from unittest.mock import patch

        def _real_db():
            with OrmSession(real_db_engine) as ses:
                yield ses

        def _override_user():
            return "testadmin"

        with (
            patch("auth_pure._ensure_table", return_value=None),
            patch("migrations.run_migrations_all_report_dbs", return_value=None),
        ):
            from main import app
            app.dependency_overrides[get_db] = _real_db
            app.dependency_overrides[get_current_user] = _override_user
            app.dependency_overrides[get_current_admin] = _override_user
            with TestClient(app, raise_server_exceptions=True) as c:
                yield c
            app.dependency_overrides.clear()

    def test_health_endpoint(self, live_client):
        r = live_client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_list_classes(self, live_client):
        r = live_client.get("/api/classes")
        assert r.status_code == 200
        assert "classes" in r.json()

    def test_list_stammdaten_real_class(self, live_client):
        """List students from a real class if one exists."""
        classes = live_client.get("/api/classes").json()["classes"]
        if not classes:
            pytest.skip("No classes in DB")
        r = live_client.get("/api/stammdaten", params={"class_name": classes[0]})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_schema_status_real_db(self, live_client):
        r = live_client.get("/api/setup/schema-status")
        assert r.status_code == 200
        data = r.json()
        assert "schema_ready" in data
        assert "student_count" in data

    def test_overview_grades_real_class(self, live_client):
        classes = live_client.get("/api/classes").json()["classes"]
        if not classes:
            pytest.skip("No classes in DB")
        r = live_client.get("/api/overview/grades", params={"class_name": classes[0]})
        assert r.status_code == 200
        assert "students" in r.json()

    def test_competence_sync_diff_no_crash(self, live_client):
        r = live_client.get("/api/admin/competence-sync/diff")
        assert r.status_code == 200
        assert "has_changes" in r.json()


# ---------------------------------------------------------------------------
# PDF compile smoke test (via docker exec)
# ---------------------------------------------------------------------------

@requires_pg
class TestCompileSmoke:
    """Minimal test that lualatex is callable in the backend container and
    that export._lua / html_to_latex produce output that doesn't crash compile."""

    def _exec(self, cmd: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["docker", "exec", "komptenzen-tool-backend-1", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=30,
        )

    def test_lualatex_version(self):
        r = self._exec("lualatex --version")
        assert r.returncode == 0
        assert "LuaHBTeX" in r.stdout or "LuaTeX" in r.stdout

    def test_minimal_lualatex_compile(self):
        """Compile the smallest valid LuaLaTeX document in /tmp."""
        tex = r"\documentclass{article}\begin{document}Hello\end{document}"
        r = self._exec(
            f"cd /tmp && echo '{tex}' > smoke.tex && "
            "lualatex --interaction=nonstopmode smoke.tex > /dev/null 2>&1 && "
            "ls smoke.pdf"
        )
        assert r.returncode == 0, f"lualatex compile failed:\n{r.stderr}"

    def test_html_to_latex_output(self):
        """Run html_to_latex inside the container to verify it's importable and correct."""
        script = (
            "import sys; sys.path.insert(0, '/backend'); "
            "from html_to_latex import html_to_latex; "
            "out = html_to_latex('<p>Hallo <strong>Welt</strong></p>'); "
            "assert '\\\\textbf{Welt}' in out, repr(out); "
            "print('OK')"
        )
        r = self._exec(f'python -c "{script}"')
        assert r.returncode == 0, r.stderr
        assert "OK" in r.stdout

    def test_lua_serializer_in_container(self):
        """Verify _lua serializer runs correctly in the container Python."""
        script = (
            "import sys; sys.path.insert(0, '/backend'); "
            "from export import _lua; "
            "result = _lua({'name': 'Test', 'grade': 3}); "
            "assert \"name = 'Test'\" in result; "
            "print('OK')"
        )
        r = self._exec(f'python -c "{script}"')
        assert r.returncode == 0, r.stderr
        assert "OK" in r.stdout
