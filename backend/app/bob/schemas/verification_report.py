"""
app/bob/schemas/verification_report.py

Pydantic schema for Verification Agent output.
See docs/features/06-verification-documentation.md.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class ComponentVerification(BaseModel):
    component_id: str
    status: Literal["passed", "failed", "unexecuted", "no_test"]
    evidence_refs: list[str] = []

    @field_validator("component_id")
    @classmethod
    def component_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("component_id must not be empty")
        return v


class UnresolvedRisk(BaseModel):
    hypothesis: str
    component_id: str
    reason_unresolved: str


class DocumentationGap(BaseModel):
    file: str
    current_text: str
    proposed_text: str
    reason: str


class VerificationReport(BaseModel):
    components_verified: list[ComponentVerification]
    unresolved_risks: list[UnresolvedRisk] = []
    documentation_gaps: list[DocumentationGap] = []
    pr_summary: str
