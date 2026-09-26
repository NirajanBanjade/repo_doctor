"""
app/bob/schemas/architecture_findings.py

Pydantic schema for Architecture Agent output.
See docs/api/contracts.md §8.
"""

from __future__ import annotations

from pydantic import BaseModel


class NodeSummary(BaseModel):
    node_id: str
    summary: str
    key_responsibilities: list[str]


class ArchitectureFindings(BaseModel):
    entry_points: list[str]
    node_summaries: list[NodeSummary]
    architectural_patterns: list[str]
    concerns: list[str]
