"""
app/bob/integration.py

Sole entry point for all IBM Bob agent invocations.
No other module may call Bob directly.
See ARCHITECTURE.md §6 and AGENTS.md §8.

OPEN QUESTION (ARCHITECTURE.md §11 item 2):
The Bob invocation API (CLI, HTTP, SDK) is not specified in the PRD.
This module is a stub. Implement only after the Bob interface is confirmed.
"""
from __future__ import annotations


class BobOutputValidationError(Exception):
    """Raised when a Bob agent response fails schema validation."""


def invoke(agent: str, payload: dict) -> dict:
    """
    Invoke a Bob agent and return the validated structured output.

    Args:
        agent: One of "architecture_agent", "documentation_agent",
               "environment_agent", "impact_agent", "test_agent",
               "contribution_agent", "verification_agent".
        payload: Dict of inputs for the agent (source snippets, graph JSON, etc.).

    Returns:
        Validated dict matching the agent's output schema.

    Raises:
        BobOutputValidationError: If the response fails schema validation.
        NotImplementedError: Until the Bob interface is confirmed.
    """
    raise NotImplementedError(
        f"Bob integration not implemented. "
        f"Cannot invoke agent '{agent}'. "
        "See ARCHITECTURE.md §11 item 2."
    )
