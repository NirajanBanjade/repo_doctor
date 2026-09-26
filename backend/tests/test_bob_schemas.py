"""
tests/test_bob_schemas.py

Unit tests for Bob output schema validation:
ArchitectureFindings and DocumentationFindings.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.bob.schemas.architecture_findings import ArchitectureFindings, NodeSummary
from app.bob.schemas.documentation_findings import (
    DocumentationFindings,
    DocumentationIssue,
)

# ── ArchitectureFindings ──────────────────────────────────────────────────────

VALID_ARCH = {
    "entry_points": ["main.py::main"],
    "node_summaries": [
        {
            "node_id": "main.py::main",
            "summary": "Application entry point",
            "key_responsibilities": ["startup", "routing"],
        }
    ],
    "architectural_patterns": ["layered"],
    "concerns": [],
}


def test_architecture_findings_valid():
    af = ArchitectureFindings.model_validate(VALID_ARCH)
    assert af.entry_points == ["main.py::main"]
    assert len(af.node_summaries) == 1
    assert af.node_summaries[0].node_id == "main.py::main"


def test_architecture_findings_empty_lists():
    af = ArchitectureFindings.model_validate(
        {
            "entry_points": [],
            "node_summaries": [],
            "architectural_patterns": [],
            "concerns": [],
        }
    )
    assert af.entry_points == []


def test_architecture_findings_missing_required_field():
    with pytest.raises(ValidationError):
        ArchitectureFindings.model_validate(
            {
                "entry_points": [],
                # node_summaries missing
                "architectural_patterns": [],
                "concerns": [],
            }
        )


def test_architecture_findings_wrong_type():
    with pytest.raises(ValidationError):
        ArchitectureFindings.model_validate(
            {
                "entry_points": "not-a-list",  # should be list
                "node_summaries": [],
                "architectural_patterns": [],
                "concerns": [],
            }
        )


def test_node_summary_missing_field():
    with pytest.raises(ValidationError):
        NodeSummary.model_validate(
            {"node_id": "x"}
        )  # summary and key_responsibilities missing


def test_architecture_findings_extra_fields_ignored():
    data = {**VALID_ARCH, "unexpected_key": "value"}
    af = ArchitectureFindings.model_validate(data)
    assert af.entry_points == ["main.py::main"]


# ── DocumentationFindings ─────────────────────────────────────────────────────

VALID_DOC = {
    "issues": [
        {"file": "README.md", "issue": "Missing setup section", "severity": "warning"}
    ],
    "setup_completeness": "partial",
    "notes": ["Consider adding a CONTRIBUTING.md"],
}


def test_documentation_findings_valid():
    df = DocumentationFindings.model_validate(VALID_DOC)
    assert df.setup_completeness == "partial"
    assert len(df.issues) == 1
    assert df.issues[0].severity == "warning"


def test_documentation_findings_missing_issues():
    with pytest.raises(ValidationError):
        DocumentationFindings.model_validate(
            {
                "setup_completeness": "complete",
                "notes": [],
                # issues missing
            }
        )


def test_documentation_findings_invalid_severity():
    with pytest.raises(ValidationError):
        DocumentationFindings.model_validate(
            {
                "issues": [
                    {"file": "f", "issue": "x", "severity": "critical"}
                ],  # invalid literal
                "setup_completeness": "complete",
                "notes": [],
            }
        )


def test_documentation_findings_invalid_completeness():
    with pytest.raises(ValidationError):
        DocumentationFindings.model_validate(
            {
                "issues": [],
                "setup_completeness": "unknown",  # not in Literal
                "notes": [],
            }
        )


def test_documentation_issue_all_severities():
    for sev in ("error", "warning", "info"):
        issue = DocumentationIssue.model_validate(
            {"file": "f.md", "issue": "test", "severity": sev}
        )
        assert issue.severity == sev
