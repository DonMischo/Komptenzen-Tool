# migrations.py
# ---------------------------------------------------------------------------
# Idempotent schema migrations applied automatically at startup and on every
# DB switch.  Add new migrations as entries in MIGRATIONS — each one is a
# (description, sql) tuple.  Every migration checks whether it is needed
# before doing anything, so re-running is always safe.
# ---------------------------------------------------------------------------
from __future__ import annotations

import logging
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Migration definitions
# Each entry: (human-readable description, SQL to run if needed, SQL check)
# The check returns 1 row with value '1' when the migration IS ALREADY done,
# and 0 rows (or value '0') when the migration still needs to run.
# ---------------------------------------------------------------------------

MIGRATIONS: list[tuple[str, str, str]] = [
    (
        "grades.value: VARCHAR(8) → TEXT",
        "ALTER TABLE grades ALTER COLUMN value TYPE TEXT",
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'grades'
          AND column_name = 'value'
          AND data_type = 'text'
        """,
    ),
]


def run_migrations(db_url: str) -> None:
    """Apply all pending migrations to the database at db_url."""
    eng = create_engine(db_url, future=True)
    try:
        with eng.connect() as conn:
            for desc, sql, check in MIGRATIONS:
                try:
                    result = conn.execute(text(check))
                    already_done = result.fetchone() is not None
                    if already_done:
                        continue
                    conn.execute(text(sql))
                    conn.commit()
                    logger.info("Migration applied: %s", desc)
                except Exception:
                    logger.warning("Migration skipped (table may not exist yet): %s", desc)
    finally:
        eng.dispose()


def run_migrations_all_report_dbs() -> None:
    """Run migrations on every reports_* database."""
    from db_schema import _pg_base_url, list_report_dbs
    base_url = _pg_base_url()
    for db_name in list_report_dbs():
        url = f"{base_url}/{db_name}"
        logger.info("Running migrations on %s", db_name)
        run_migrations(url)
