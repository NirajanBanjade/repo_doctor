"""
app/bob/schemas/test_plan.py

Pydantic schema for Test Agent output (TestPlanProposal).
See docs/features/05-radius-test-generator.md §Test Agent invocation.
"""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class TestScenario(BaseModel):
    name: str
    component_id: str  # maps to a graph node_id
    source_evidence: str  # file:line reference
    expected_behavior: str
    proposed_test_file: str  # relative path in working_copy
    proposed_test_function: str

    @field_validator("component_id")
    @classmethod
    def _component_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("component_id must not be empty")
        return v


class TestPlanProposal(BaseModel):
    scenarios: list[TestScenario]
    analysis_notes: list[str] = []
