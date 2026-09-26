"""
app/api/routes/sessions.py

POST /api/v1/sessions   — create a new session
GET  /api/v1/sessions/{session_id}  — retrieve session state
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import session as session_svc

router = APIRouter()


class CreateSessionRequest(BaseModel):
    repo_path: str


@router.post("", status_code=201)
async def create_session(body: CreateSessionRequest) -> dict:
    try:
        repo_path = Path(body.repo_path).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise HTTPException(
            status_code=422, detail="Repository path does not exist"
        ) from exc

    if not repo_path.is_dir():
        raise HTTPException(
            status_code=422, detail="Repository path is not a directory"
        )

    return session_svc.create_session(str(repo_path))


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s
