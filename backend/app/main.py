"""
app/main.py

FastAPI application entry point.
Routes are registered here but not yet implemented.
See ARCHITECTURE.md §7 for the full API design.
"""
from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import (
    environment,
    impact,
    sessions,
    tests,
    verification,
    xray,
)

app = FastAPI(title="RepoDoc API", version="0.1.0")

app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(xray.router, prefix="/api/v1/sessions", tags=["xray"])
app.include_router(environment.router, prefix="/api/v1/sessions", tags=["environment"])
app.include_router(impact.router, prefix="/api/v1/sessions", tags=["impact"])
app.include_router(tests.router, prefix="/api/v1/sessions", tags=["tests"])
app.include_router(verification.router, prefix="/api/v1/sessions", tags=["verification"])
