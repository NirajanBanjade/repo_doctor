"""
app/db/models.py

SQLAlchemy Core table definitions for the RepoDoc evidence store.
See ARCHITECTURE.md §9 for the full schema.
"""

from __future__ import annotations

import sqlalchemy as sa

metadata = sa.MetaData()

sessions = sa.Table(
    "sessions",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column("repo_path", sa.String, nullable=False),
    sa.Column("status", sa.String, nullable=False, default="created"),
    sa.Column("stack", sa.JSON, nullable=True),
    sa.Column("created_at", sa.DateTime, nullable=False),
    sa.Column("updated_at", sa.DateTime, nullable=False),
)

graph_nodes = sa.Table(
    "graph_nodes",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False),
    sa.Column("node_id", sa.String, nullable=False),
    sa.Column("kind", sa.String, nullable=False),
    sa.Column("name", sa.String, nullable=False),
    sa.Column("path", sa.String, nullable=False),
    sa.Column("line_start", sa.Integer, nullable=False),
    sa.Column("line_end", sa.Integer, nullable=False),
    sa.Column("language", sa.String, nullable=False),
    sa.Column("summary", sa.String, nullable=True),
    sa.Column("key_module", sa.Boolean, nullable=False, default=False),
)

graph_edges = sa.Table(
    "graph_edges",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False),
    sa.Column("edge_id", sa.String, nullable=False),
    sa.Column("source_id", sa.String, nullable=False),
    sa.Column("target_id", sa.String, nullable=False),
    sa.Column("relationship", sa.String, nullable=False),
    sa.Column("file", sa.String, nullable=False),
    sa.Column("line", sa.Integer, nullable=False),
    sa.Column("evidence_status", sa.String, nullable=False),
    sa.Column("note", sa.String, nullable=True),
)

bob_outputs = sa.Table(
    "bob_outputs",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False),
    sa.Column("agent", sa.String, nullable=False),
    sa.Column("raw_output", sa.Text, nullable=False),
    sa.Column("parsed_ok", sa.Boolean, nullable=False),
    sa.Column("created_at", sa.DateTime, nullable=False),
)
