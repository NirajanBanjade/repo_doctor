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

environment_checks = sa.Table(
    "environment_checks",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False),
    sa.Column("step_id", sa.String, nullable=False),
    sa.Column("command", sa.String, nullable=False),
    sa.Column(
        "status", sa.String, nullable=False
    ),  # verified | failed | blocked | infrastructure_error
    sa.Column("exit_code", sa.Integer, nullable=True),
    sa.Column("stdout", sa.Text, nullable=True),
    sa.Column("stderr", sa.Text, nullable=True),
    sa.Column("started_at", sa.DateTime, nullable=True),
    sa.Column("finished_at", sa.DateTime, nullable=True),
    sa.Column("run_number", sa.Integer, nullable=False, default=1),
)

test_plans = sa.Table(
    "test_plans",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("plan_id", sa.String, nullable=False, unique=True),
    sa.Column("session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False),
    sa.Column(
        "impact_run_id",
        sa.String,
        sa.ForeignKey("impact_results.run_id"),
        nullable=False,
    ),
    sa.Column("scenarios", sa.JSON, nullable=False),
    sa.Column(
        "status", sa.String, nullable=False, default="pending"
    ),  # pending | approved | rejected
    sa.Column("created_at", sa.DateTime, nullable=False),
)

test_results = sa.Table(
    "test_results",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("result_id", sa.String, nullable=False, unique=True),
    sa.Column(
        "plan_id", sa.String, sa.ForeignKey("test_plans.plan_id"), nullable=False
    ),
    sa.Column("session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False),
    sa.Column("stdout", sa.Text, nullable=True),
    sa.Column("stderr", sa.Text, nullable=True),
    sa.Column("exit_code", sa.Integer, nullable=True),
    sa.Column("infrastructure_error", sa.Boolean, nullable=False, default=False),
    sa.Column("per_test", sa.JSON, nullable=False),  # list of {nodeid, outcome}
    sa.Column("component_statuses", sa.JSON, nullable=False),
    sa.Column("created_at", sa.DateTime, nullable=False),
)

impact_results = sa.Table(
    "impact_results",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("run_id", sa.String, nullable=False, unique=True),
    sa.Column("session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False),
    sa.Column("origin_ids", sa.JSON, nullable=False),
    sa.Column("depth", sa.Integer, nullable=False),
    sa.Column("change_description", sa.Text, nullable=True),
    sa.Column("unresolved_symbols", sa.JSON, nullable=False),
    sa.Column("created_at", sa.DateTime, nullable=False),
)

impact_nodes = sa.Table(
    "impact_nodes",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column(
        "run_id", sa.String, sa.ForeignKey("impact_results.run_id"), nullable=False
    ),
    sa.Column("node_id", sa.String, nullable=False),
    sa.Column("depth_level", sa.Integer, nullable=False),
)

verification_reports = sa.Table(
    "verification_reports",
    metadata,
    sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
    sa.Column("report_id", sa.String, nullable=False, unique=True),
    sa.Column("session_id", sa.String, sa.ForeignKey("sessions.id"), nullable=False),
    sa.Column("components_verified", sa.JSON, nullable=False),
    sa.Column("unresolved_risks", sa.JSON, nullable=False),
    sa.Column("documentation_gaps", sa.JSON, nullable=False),
    sa.Column("pr_summary", sa.Text, nullable=False),
    sa.Column("created_at", sa.DateTime, nullable=False),
)
