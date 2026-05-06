# main.py — FastAPI application factory
from __future__ import annotations

import logging
logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import auth_pure
from routers import auth, setup, competences, students, stammdaten, admin

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
