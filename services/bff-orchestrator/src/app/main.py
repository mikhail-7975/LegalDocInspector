"""FastAPI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

# Repo root must be on sys.path for LegalDocInspector and configs
def _bootstrap_sys_path() -> Path:
    root = Path(__file__).resolve().parents[4]
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root


_bootstrap_sys_path()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes import auth, health, packages
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Legal Doc Claim BFF", version="0.1.0")

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(packages.router, prefix="/api/v1")
