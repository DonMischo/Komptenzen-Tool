# main.py — FastAPI application factory
from __future__ import annotations

import logging
logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import auth_pure
from routers import auth, setup, competences, students, stammdaten, admin, overview
from db_schema import Subject
from competence_data import SUBJECTS as _ALL_SUBJECTS
from sqlalchemy.orm import Session as _Session
from migrations import run_migrations_all_report_dbs

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure admin_users table exists in postgres DB at startup
    try:
        auth_pure._ensure_table()
        logger.info("auth_pure: admin_users table ready")
    except Exception:
        logger.exception("FATAL: could not create admin_users table — check POSTGRES_URL")
        raise

    # Run schema migrations on all existing report databases
    try:
        run_migrations_all_report_dbs()
    except Exception:
        logger.warning("Could not run migrations (DB may not be reachable yet)")

    # Ensure Subject rows exist in all report DBs for all SUBJECTS entries (e.g. Lebenspraxis)
    try:
        from db_schema import _pg_base_url, list_report_dbs, _make_engine
        for db_name in list_report_dbs():
            eng = _make_engine(db_name)
            try:
                with _Session(eng) as ses:
                    for name in _ALL_SUBJECTS:
                        if not ses.query(Subject).filter_by(name=name).first():
                            ses.add(Subject(name=name))
                    ses.commit()
            finally:
                eng.dispose()
        logger.info("Subject rows ensured")
    except Exception:
        logger.warning("Could not ensure Subject rows (DB may not be reachable yet)")
    yield


app = FastAPI(title="Kompetenzen-Tool API", version="1.0.0", lifespan=lifespan)

# CORS only needed in development (Next.js dev server on :3000, backend on :8000).
# In production the Next.js server proxies /api/* → backend, so no CORS needed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/auth",       tags=["auth"])
app.include_router(setup.router,       prefix="/api",            tags=["setup"])
app.include_router(competences.router, prefix="/api",            tags=["competences"])
app.include_router(students.router,    prefix="/api/students",   tags=["students"])
app.include_router(stammdaten.router,  prefix="/api/stammdaten", tags=["stammdaten"])
app.include_router(admin.router,       prefix="/api/admin",      tags=["admin"])
app.include_router(overview.router,    prefix="/api/overview",   tags=["overview"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
