"""
app/bob/schemas/environment_diagnosis.py

Pydantic schema for Environment Agent output.
See docs/features/02-environment-doctor.md.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class EnvironmentDiagnosis(BaseModel):
    root_cause: str
    proposed_fix: str
    patch: str | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
