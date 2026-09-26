"""
app/main.py

FastAPI application entry point.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import (
    environment,
    impact,
    sessions,
    tests,
    verification,
    xray,
)
from app.db.evidence_store import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="RepoDoc API", version="0.1.0", lifespan=lifespan)

app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(xray.router, prefix="/api/v1/sessions", tags=["xray"])
app.include_router(environment.router, prefix="/api/v1/sessions", tags=["environment"])
app.include_router(impact.router, prefix="/api/v1/sessions", tags=["impact"])
app.include_router(tests.router, prefix="/api/v1/sessions", tags=["tests"])
app.include_router(
    verification.router, prefix="/api/v1/sessions", tags=["verification"]
)
