"""
app/bob/schemas/documentation_findings.py

Pydantic schema for Documentation Agent output.
See docs/api/contracts.md §8.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class DocumentationIssue(BaseModel):
    file: str
    issue: str
    severity: Literal["error", "warning", "info"]


class DocumentationFindings(BaseModel):
    issues: list[DocumentationIssue]
    setup_completeness: Literal["complete", "partial", "missing"]
    notes: list[str]
