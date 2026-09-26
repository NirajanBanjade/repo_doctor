"""
app/services/environment_doctor.py

Setup plan builder: parses README/setup docs and extracts shell commands.
Execution is delegated to app/sandbox/docker_runner.py.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field

# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class SetupStep:
    step_id: str
    command: str
    expected_exit_code: int = 0
    timeout_s: int = 120


@dataclass
class SetupPlan:
    steps: list[SetupStep] = field(default_factory=list)


# ── README section keywords ───────────────────────────────────────────────────

_SECTION_KEYWORDS = re.compile(
    r"(setup|install|getting.started|prerequisites|quick.start|development)",
    re.IGNORECASE,
)

# Matches fenced code blocks: ```[lang]\n...\n```  or indented (4-space) blocks
_FENCED_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_SHELL_CMD = re.compile(
    r"^\$?\s*((?:pip|python|npm|yarn|make|docker|poetry|uv|bash|sh|cargo|go|mvn|gradle|./[\w./]+).*)",
    re.MULTILINE,
)


def _is_setup_section(heading: str) -> bool:
    return bool(_SECTION_KEYWORDS.search(heading))


def _extract_commands_from_text(text: str) -> list[str]:
    """Pull shell commands out of fenced code blocks in the given text."""
    commands: list[str] = []
    for block in _FENCED_BLOCK.finditer(text):
        content = block.group(1)
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Strip leading `$ ` prompt if present
            line = line.removeprefix("$ ")
            commands.append(line)
    return commands


def build_setup_plan(readme_content: str) -> SetupPlan:
    """
    Parse a README and return an ordered SetupPlan.

    Strategy:
    1. Split on Markdown headings (# / ## / ###).
    2. Keep sections whose headings contain setup keywords.
    3. Extract commands from fenced code blocks inside those sections.
    4. Fall back to the whole document if no setup-tagged sections are found.
    """
    # Split into (heading, body) pairs.
    # Temporarily blank out fenced code blocks so comment lines inside them
    # (e.g. `# install deps`) are not mistaken for Markdown headings.
    _BLANK_FENCED = re.compile(r"```[^\n]*\n.*?```", re.DOTALL)
    sanitised = _BLANK_FENCED.sub(
        lambda m: "\n" * m.group(0).count("\n"), readme_content
    )
    heading_re = re.compile(r"^(#{1,4} .+)$", re.MULTILINE)
    # Split the sanitised text, but extract bodies from the *original* content
    # using the same span positions.
    split_positions = [0]
    headings: list[str] = []
    for m in heading_re.finditer(sanitised):
        split_positions.append(m.start())
        split_positions.append(m.end())
        headings.append(m.group(1))
    split_positions.append(len(readme_content))

    # Build (heading, body) pairs from original content
    sections: list[tuple[str, str]] = []
    if split_positions[0] < split_positions[1]:
        sections.append(
            ("preamble", readme_content[split_positions[0] : split_positions[1]])
        )
    for idx, heading in enumerate(headings):
        body_start = split_positions[idx * 2 + 2]
        body_end = split_positions[idx * 2 + 3]
        sections.append((heading, readme_content[body_start:body_end]))

    setup_sections = [body for heading, body in sections if _is_setup_section(heading)]
    if not setup_sections:
        # Fall back: scan the whole document
        setup_sections = [readme_content]

    commands: list[str] = []
    for body in setup_sections:
        commands.extend(_extract_commands_from_text(body))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique_commands: list[str] = []
    for cmd in commands:
        if cmd not in seen:
            seen.add(cmd)
            unique_commands.append(cmd)

    steps = [
        SetupStep(step_id=str(uuid.uuid4()), command=cmd) for cmd in unique_commands
    ]
    return SetupPlan(steps=steps)
