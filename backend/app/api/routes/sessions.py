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
    architecture_path: str | None = None


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

    architecture_path: Path | None = None
    if body.architecture_path:
        supplied = Path(body.architecture_path).expanduser()
        architecture_path = supplied if supplied.is_absolute() else repo_path / supplied
        try:
            architecture_path = architecture_path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise HTTPException(
                status_code=422, detail="Architecture wiki directory does not exist"
            ) from exc
        if not architecture_path.is_dir():
            raise HTTPException(
                status_code=422, detail="Architecture wiki path is not a directory"
            )
        feature_pages = [
            page
            for page in architecture_path.glob("*.md")
            if page.name.lower() != "readme.md"
        ]
        if not feature_pages:
            raise HTTPException(
                status_code=422,
                detail="Architecture wiki contains no feature Markdown files",
            )

    return session_svc.create_session(
        str(repo_path), str(architecture_path) if architecture_path else None
    )


@router.get("/{session_id}")
async def get_session(session_id: str) -> dict:
    s = session_svc.get_session(session_id)
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return s
