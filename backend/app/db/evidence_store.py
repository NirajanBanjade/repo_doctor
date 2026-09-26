"""
app/db/evidence_store.py

Read/write interface for the SQLite evidence store.
All DB access goes through this module.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa

from app.analysis.base_adapter import GraphEdge, GraphNode
from app.db.models import (
    bob_outputs,
    environment_checks,
    graph_edges,
    graph_nodes,
    metadata,
    sessions,
)

_engine: sa.Engine | None = None


def get_engine(db_url: str = "sqlite:///./repodoc.db") -> sa.Engine:
    global _engine
    if _engine is None:
        _engine = sa.create_engine(db_url, connect_args={"check_same_thread": False})
        metadata.create_all(_engine)
    return _engine


def init_db(db_url: str = "sqlite:///./repodoc.db") -> None:
    """Initialise tables. Call once at startup."""
    get_engine(db_url)


# ── Sessions ──────────────────────────────────────────────────────────────────


def create_session(repo_path: str, db_url: str = "sqlite:///./repodoc.db") -> dict:
    engine = get_engine(db_url)
    now = datetime.now(timezone.utc)
    sid = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(
            sessions.insert().values(
                id=sid,
                repo_path=repo_path,
                status="created",
                stack=None,
                created_at=now,
                updated_at=now,
            )
        )
    return _row_to_session(sid, repo_path, "created", None, now, now)


def get_session(session_id: str, db_url: str = "sqlite:///./repodoc.db") -> dict | None:
    engine = get_engine(db_url)
    with engine.connect() as conn:
        row = conn.execute(
            sessions.select().where(sessions.c.id == session_id)
        ).fetchone()
    if row is None:
        return None
    return _row_to_session(*row)


def update_session_status(
    session_id: str,
    status: str,
    stack: dict | None = None,
    db_url: str = "sqlite:///./repodoc.db",
) -> None:
    engine = get_engine(db_url)
    vals: dict = {"status": status, "updated_at": datetime.now(timezone.utc)}
    if stack is not None:
        vals["stack"] = stack
    with engine.begin() as conn:
        conn.execute(
            sessions.update().where(sessions.c.id == session_id).values(**vals)
        )


def _row_to_session(sid, repo_path, status, stack, created_at, updated_at) -> dict:
    return {
        "session_id": sid,
        "repo_path": repo_path,
        "status": status,
        "stack": stack,
        "created_at": (
            created_at.isoformat() if hasattr(created_at, "isoformat") else created_at
        ),
        "updated_at": (
            updated_at.isoformat() if hasattr(updated_at, "isoformat") else updated_at
        ),
    }


# ── Graph nodes/edges ─────────────────────────────────────────────────────────


def save_nodes(
    session_id: str, nodes: list[GraphNode], db_url: str = "sqlite:///./repodoc.db"
) -> None:
    if not nodes:
        return
    engine = get_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            graph_nodes.insert(),
            [
                {
                    "session_id": session_id,
                    "node_id": n.node_id,
                    "kind": n.kind,
                    "name": n.name,
                    "path": n.path,
                    "line_start": n.line_start,
                    "line_end": n.line_end,
                    "language": n.language,
                    "summary": n.summary,
                    "key_module": n.key_module,
                }
                for n in nodes
            ],
        )


def save_edges(
    session_id: str, edges: list[GraphEdge], db_url: str = "sqlite:///./repodoc.db"
) -> None:
    if not edges:
        return
    engine = get_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            graph_edges.insert(),
            [
                {
                    "session_id": session_id,
                    "edge_id": str(uuid.uuid4()),
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relationship": e.relationship,
                    "file": e.file,
                    "line": e.line,
                    "evidence_status": e.evidence_status,
                    "note": e.note,
                }
                for e in edges
            ],
        )


def get_nodes(session_id: str, db_url: str = "sqlite:///./repodoc.db") -> list[dict]:
    engine = get_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(
            graph_nodes.select().where(graph_nodes.c.session_id == session_id)
        ).fetchall()
    return [row._mapping for row in rows]


def get_edges(session_id: str, db_url: str = "sqlite:///./repodoc.db") -> list[dict]:
    engine = get_engine(db_url)
    with engine.connect() as conn:
        rows = conn.execute(
            graph_edges.select().where(graph_edges.c.session_id == session_id)
        ).fetchall()
    return [row._mapping for row in rows]


# ── Bob outputs ───────────────────────────────────────────────────────────────


def save_bob_output(
    session_id: str,
    agent: str,
    raw_output: str,
    parsed_ok: bool,
    db_url: str = "sqlite:///./repodoc.db",
) -> None:
    engine = get_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            bob_outputs.insert().values(
                session_id=session_id,
                agent=agent,
                raw_output=raw_output,
                parsed_ok=parsed_ok,
                created_at=datetime.now(timezone.utc),
            )
        )


# ── Environment checks ────────────────────────────────────────────────────────


def save_environment_check(
    session_id: str,
    step_id: str,
    command: str,
    status: str,
    run_number: int = 1,
    exit_code: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    db_url: str = "sqlite:///./repodoc.db",
) -> None:
    engine = get_engine(db_url)
    with engine.begin() as conn:
        conn.execute(
            environment_checks.insert().values(
                session_id=session_id,
                step_id=step_id,
                command=command,
                status=status,
                run_number=run_number,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                started_at=started_at,
                finished_at=finished_at,
            )
        )


def get_environment_checks(
    session_id: str,
    run_number: int | None = None,
    db_url: str = "sqlite:///./repodoc.db",
) -> list[dict]:
    engine = get_engine(db_url)
    query = environment_checks.select().where(
        environment_checks.c.session_id == session_id
    )
    if run_number is not None:
        query = query.where(environment_checks.c.run_number == run_number)
    query = query.order_by(environment_checks.c.id)
    with engine.connect() as conn:
        rows = conn.execute(query).fetchall()
    return [dict(r._mapping) for r in rows]
