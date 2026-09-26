"""
app/bob/integration.py

Sole entry point for all IBM Bob agent invocations.
Degrades gracefully when Bob is unavailable — callers receive None.
See ARCHITECTURE.md §6 and AGENTS.md §8.

OPEN QUESTION (ARCHITECTURE.md §11 item 2):
The concrete Bob invocation API (CLI, HTTP, SDK) is not specified.
This module uses a stub that logs and returns None; wire up the real
interface once it is confirmed.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from app.bob.schemas.architecture_findings import ArchitectureFindings
from app.bob.schemas.documentation_findings import DocumentationFindings
from app.db import evidence_store

logger = logging.getLogger(__name__)


class BobOutputValidationError(Exception):
    """Raised when a Bob agent response fails schema validation."""


# ── Low-level stub (replace with real Bob SDK call) ───────────────────────────


async def _call_bob(agent: str, payload: dict) -> dict | None:
    """
    Invoke the Bob agent API. Returns the raw dict or None on failure.
    Replace this implementation once the Bob interface is confirmed.
    """
    # TODO: replace with real Bob invocation (ARCHITECTURE.md §11 item 2)
    logger.warning(
        "bob/integration: Bob interface not yet wired — agent=%s unavailable", agent
    )
    return None


# ── Public async helpers ──────────────────────────────────────────────────────


async def run_xray_agents(
    session_id: str,
    nodes: list[dict],
    stack: dict,
    readme_excerpt: str,
    doc_files: dict[str, str],
    db_url: str = "sqlite:///./repodoc.db",
) -> tuple[ArchitectureFindings | None, DocumentationFindings | None]:
    """
    Launch Architecture Agent and Documentation Agent concurrently.
    Returns (ArchitectureFindings | None, DocumentationFindings | None).
    Gracefully returns None for each agent that fails or is unavailable.
    """
    arch_payload = {
        "nodes": nodes,
        "stack": stack,
        "readme_excerpt": readme_excerpt,
    }
    doc_payload = {"doc_files": doc_files}

    arch_raw, doc_raw = await asyncio.gather(
        _call_bob("architecture_agent", arch_payload),
        _call_bob("documentation_agent", doc_payload),
        return_exceptions=False,
    )

    arch_findings = _validate_and_store(
        session_id,
        "architecture_agent",
        arch_raw,
        ArchitectureFindings,
        db_url,
    )
    doc_findings = _validate_and_store(
        session_id,
        "documentation_agent",
        doc_raw,
        DocumentationFindings,
        db_url,
    )
    return arch_findings, doc_findings


def _validate_and_store(
    session_id: str,
    agent: str,
    raw: dict | None,
    schema: type,
    db_url: str,
) -> Any | None:
    raw_str = json.dumps(raw) if raw is not None else ""
    if raw is None:
        evidence_store.save_bob_output(
            session_id, agent, raw_str, parsed_ok=False, db_url=db_url
        )
        return None
    try:
        result = schema.model_validate(raw)
        evidence_store.save_bob_output(
            session_id, agent, raw_str, parsed_ok=True, db_url=db_url
        )
        return result
    except ValidationError as exc:
        logger.error(
            "bob/integration: schema validation failed agent=%s: %s", agent, exc
        )
        evidence_store.save_bob_output(
            session_id, agent, raw_str, parsed_ok=False, db_url=db_url
        )
        return None
