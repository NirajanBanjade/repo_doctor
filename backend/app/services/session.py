"""
app/services/session.py

Session lifecycle management.
"""

from __future__ import annotations

from app.db import evidence_store


def create_session(repo_path: str, db_url: str = "sqlite:///./repodoc.db") -> dict:
    return evidence_store.create_session(repo_path, db_url=db_url)


def get_session(session_id: str, db_url: str = "sqlite:///./repodoc.db") -> dict | None:
    return evidence_store.get_session(session_id, db_url=db_url)


def update_status(
    session_id: str,
    status: str,
    stack: dict | None = None,
    db_url: str = "sqlite:///./repodoc.db",
) -> None:
    evidence_store.update_session_status(session_id, status, stack=stack, db_url=db_url)
