"""
app/bob/schemas/impact_annotations.py

Pydantic schema for Impact Agent output.
See docs/api/contracts.md §8 (ImpactAnnotations).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class ImpactAnnotation(BaseModel):
    node_id: str
    risk: str
    hypothesis_label: str = "hypothesis"
    evidence_status: Literal["inferred"] = "inferred"


class ImpactAnnotations(BaseModel):
    annotations: list[ImpactAnnotation]
    analysis_notes: list[str] = []
