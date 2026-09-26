"""
app/services/verification.py

Evidence aggregation and documentation patch generation for Feature 06.
Collects test results, impact nodes, environment checks, and Bob outputs
for a session, then assembles a structured evidence summary and generates
unified-diff patches for documentation gaps.
"""

from __future__ import annotations

import difflib
import logging
import os
from pathlib import Path

from app.db import evidence_store

logger = logging.getLogger(__name__)

# Status mapping from component_statuses entries to VerificationReport statuses
_STATUS_MAP = {
    "covered_passed": "passed",
    "covered_failed": "failed",
    "unexecuted": "unexecuted",
    "no_suitable_test": "no_test",
}


def aggregate_evidence(session_id: str, db_url: str = "sqlite:///./repodoc.db") -> dict:
    """
    Gather all evidence for a session and return a structured summary dict
    suitable for passing to the Verification Agent or for building a fallback report.

    Returns:
        {
            "change_description": str | None,
            "impact_run": dict | None,
            "impact_node_ids": list[str],
            "component_statuses": list[dict],   # from latest test result
            "per_test": list[dict],
            "infrastructure_error": bool,
            "inferred_node_ids": list[str],      # impact nodes with inferred edges
            "env_checks": list[dict],
        }
    """
    impact_run = evidence_store.get_latest_impact_run(session_id, db_url)
    impact_node_ids: list[str] = []
    component_statuses: list[dict] = []
    per_test: list[dict] = []
    infrastructure_error = False
    inferred_node_ids: list[str] = []

    if impact_run:
        nodes = evidence_store.get_impact_nodes(impact_run["run_id"], db_url)
        impact_node_ids = [n["node_id"] for n in nodes]

        plan = evidence_store.get_test_plan_by_impact_run(impact_run["run_id"], db_url)
        if plan:
            result = evidence_store.get_test_result_by_plan(plan["plan_id"], db_url)
            if result:
                component_statuses = result.get("component_statuses") or []
                per_test = result.get("per_test") or []
                infrastructure_error = bool(result.get("infrastructure_error"))

        # Identify impact nodes whose graph edges are all inferred
        all_edges = evidence_store.get_edges(session_id, db_url)
        inferred_targets = {
            e["target_id"]
            for e in all_edges
            if e["evidence_status"] == "inferred"
        }
        inferred_node_ids = [nid for nid in impact_node_ids if nid in inferred_targets]

    env_checks = evidence_store.get_environment_checks(session_id, db_url=db_url)

    return {
        "change_description": impact_run.get("change_description") if impact_run else None,
        "impact_run": impact_run,
        "impact_node_ids": impact_node_ids,
        "component_statuses": component_statuses,
        "per_test": per_test,
        "infrastructure_error": infrastructure_error,
        "inferred_node_ids": inferred_node_ids,
        "env_checks": env_checks,
    }


def build_fallback_report(evidence: dict) -> dict:
    """
    Construct a VerificationReport-shaped dict from raw evidence when Bob is
    unavailable.  All inferred nodes with no test become unresolved_risks.
    """
    impact_node_ids: list[str] = evidence["impact_node_ids"]
    component_statuses: list[dict] = evidence["component_statuses"]
    inferred_node_ids: set[str] = set(evidence["inferred_node_ids"])

    # Build a lookup from component_id → status
    cs_map = {cs["component_id"]: cs["status"] for cs in component_statuses}

    components_verified = []
    for nid in impact_node_ids:
        raw_status = cs_map.get(nid, "no_suitable_test")
        status = _STATUS_MAP.get(raw_status, "no_test")
        # Collect evidence refs from per_test entries
        refs = [
            t["nodeid"]
            for t in evidence["per_test"]
            if nid in t.get("nodeid", "")
        ]
        components_verified.append(
            {
                "component_id": nid,
                "status": status,
                "evidence_refs": refs,
            }
        )

    # Nodes with inferred edges that have no test coverage are unresolved risks
    unresolved_risks = [
        {
            "hypothesis": f"Behaviour of {nid} under change is unverified",
            "component_id": nid,
            "reason_unresolved": (
                "Edge to this component is inferred (dynamic/unresolved call) "
                "and no test covers it."
            ),
        }
        for nid in inferred_node_ids
        if cs_map.get(nid) in (None, "no_suitable_test")
    ]

    change_description = evidence.get("change_description") or "(no change description provided)"
    pr_summary = _build_pr_summary(change_description, components_verified, unresolved_risks)

    return {
        "components_verified": components_verified,
        "unresolved_risks": unresolved_risks,
        "documentation_gaps": [],
        "pr_summary": pr_summary,
    }


def _build_pr_summary(
    change_description: str,
    components_verified: list[dict],
    unresolved_risks: list[dict],
) -> str:
    lines = [
        "## PR Summary (generated by RepoDoc — must be reviewed before submission)",
        "",
        f"**Change description:** {change_description}",
        "",
        "### Test Results",
        "",
        "| Component | Status | Evidence |",
        "|---|---|---|",
    ]
    for cv in components_verified:
        refs = ", ".join(cv["evidence_refs"]) if cv["evidence_refs"] else "—"
        lines.append(f"| `{cv['component_id']}` | {cv['status']} | {refs} |")

    if unresolved_risks:
        lines += [
            "",
            "### Unresolved Risks (hypotheses)",
            "",
        ]
        for risk in unresolved_risks:
            lines.append(
                f"- **`{risk['component_id']}`**: {risk['hypothesis']}  \n"
                f"  _Reason unresolved_: {risk['reason_unresolved']}"
            )

    lines += [
        "",
        "> **Note:** This summary was generated by RepoDoc and must be reviewed before submission.",
    ]
    return "\n".join(lines)


def generate_documentation_patches(
    documentation_gaps: list[dict],
    working_copy_root: str,
) -> list[str]:
    """
    For each documentation gap, generate a unified diff and write it to
    working_copy/docs/fixes/{filename}.patch.
    Returns a list of written patch file paths.
    NEVER modifies the original repository files.
    """
    patches_dir = Path(working_copy_root) / "docs" / "fixes"
    patches_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for gap in documentation_gaps:
        filename = os.path.basename(gap["file"])
        patch_path = patches_dir / f"{filename}.patch"

        before_lines = gap["current_text"].splitlines(keepends=True)
        after_lines = gap["proposed_text"].splitlines(keepends=True)
        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{gap['file']}",
            tofile=f"b/{gap['file']}",
        )
        patch_content = "".join(diff)
        patch_path.write_text(patch_content)
        written.append(str(patch_path))
        logger.info("verification: wrote documentation patch %s", patch_path)

    return written
