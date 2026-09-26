"""
tests/test_environment_doctor.py

Unit tests for the Environment Doctor service and EnvironmentDiagnosis schema.
Covers:
  - SetupPlan builder: command extraction from various README styles
  - EnvironmentDiagnosis schema: valid/invalid payloads
"""

from __future__ import annotations

import textwrap

import pytest
from pydantic import ValidationError

from app.bob.schemas.environment_diagnosis import EnvironmentDiagnosis
from app.services.environment_doctor import build_setup_plan

# ── build_setup_plan — command extraction ────────────────────────────────────


def test_extracts_commands_from_setup_section():
    readme = textwrap.dedent("""
        # My Project

        ## Installation

        ```bash
        pip install -r requirements.txt
        python -m pytest
        ```
    """)
    plan = build_setup_plan(readme)
    commands = [s.command for s in plan.steps]
    assert "pip install -r requirements.txt" in commands
    assert "python -m pytest" in commands


def test_strips_dollar_sign_prompt():
    readme = textwrap.dedent("""
        ## Setup

        ```
        $ pip install -r requirements.txt
        $ python app.py
        ```
    """)
    plan = build_setup_plan(readme)
    commands = [s.command for s in plan.steps]
    assert "pip install -r requirements.txt" in commands
    assert "python app.py" in commands
    # Dollar sign must not be present
    for cmd in commands:
        assert not cmd.startswith("$")


def test_skips_comment_lines_inside_fenced_block():
    readme = textwrap.dedent("""
        ## Getting Started

        ```bash
        # install dependencies
        pip install -r requirements.txt
        # run tests
        pytest
        ```
    """)
    plan = build_setup_plan(readme)
    commands = [s.command for s in plan.steps]
    assert all(not c.startswith("#") for c in commands)
    assert "pip install -r requirements.txt" in commands
    assert "pytest" in commands


def test_multiple_code_blocks_in_same_section():
    readme = textwrap.dedent("""
        ## Installation

        Install dependencies:

        ```bash
        pip install -r requirements.txt
        ```

        Run the server:

        ```bash
        python main.py
        ```
    """)
    plan = build_setup_plan(readme)
    commands = [s.command for s in plan.steps]
    assert "pip install -r requirements.txt" in commands
    assert "python main.py" in commands


def test_deduplicates_commands():
    readme = textwrap.dedent("""
        ## Setup

        ```bash
        pip install -r requirements.txt
        pip install -r requirements.txt
        python -m pytest
        ```
    """)
    plan = build_setup_plan(readme)
    commands = [s.command for s in plan.steps]
    assert commands.count("pip install -r requirements.txt") == 1


def test_falls_back_to_whole_document_when_no_setup_section():
    readme = textwrap.dedent("""
        # My App

        ```bash
        pip install flask
        ```
    """)
    plan = build_setup_plan(readme)
    commands = [s.command for s in plan.steps]
    assert "pip install flask" in commands


def test_returns_empty_plan_when_no_code_blocks():
    readme = "# My App\n\nJust some description without code blocks.\n"
    plan = build_setup_plan(readme)
    assert plan.steps == []


def test_each_step_has_unique_step_id():
    readme = textwrap.dedent("""
        ## Setup

        ```bash
        pip install -r requirements.txt
        python -m pytest
        ```
    """)
    plan = build_setup_plan(readme)
    ids = [s.step_id for s in plan.steps]
    assert len(ids) == len(set(ids))


def test_default_expected_exit_code_is_zero():
    readme = textwrap.dedent("""
        ## Installation

        ```bash
        pip install -r requirements.txt
        ```
    """)
    plan = build_setup_plan(readme)
    for step in plan.steps:
        assert step.expected_exit_code == 0


def test_getting_started_heading_is_recognised():
    readme = textwrap.dedent("""
        ## Getting Started

        ```bash
        npm install
        npm start
        ```
    """)
    plan = build_setup_plan(readme)
    commands = [s.command for s in plan.steps]
    assert "npm install" in commands


def test_prerequisites_heading_is_recognised():
    readme = textwrap.dedent("""
        ## Prerequisites

        ```bash
        docker build -t myapp .
        ```
    """)
    plan = build_setup_plan(readme)
    commands = [s.command for s in plan.steps]
    assert "docker build -t myapp ." in commands


# ── EnvironmentDiagnosis schema ───────────────────────────────────────────────


def test_valid_environment_diagnosis():
    data = {
        "root_cause": "Missing dependency: libpq-dev",
        "proposed_fix": "Run apt-get install libpq-dev before pip install",
        "patch": None,
        "confidence": "high",
    }
    diag = EnvironmentDiagnosis.model_validate(data)
    assert diag.root_cause == "Missing dependency: libpq-dev"
    assert diag.confidence == "high"


def test_diagnosis_requires_root_cause():
    data = {
        "proposed_fix": "Run apt-get install libpq-dev",
        "confidence": "medium",
    }
    with pytest.raises(ValidationError) as exc_info:
        EnvironmentDiagnosis.model_validate(data)
    assert "root_cause" in str(exc_info.value)


def test_diagnosis_requires_proposed_fix():
    data = {
        "root_cause": "Some root cause",
        "confidence": "low",
    }
    with pytest.raises(ValidationError) as exc_info:
        EnvironmentDiagnosis.model_validate(data)
    assert "proposed_fix" in str(exc_info.value)


def test_diagnosis_rejects_invalid_confidence():
    data = {
        "root_cause": "Something",
        "proposed_fix": "Fix it",
        "confidence": "very_high",  # not in Literal["high", "medium", "low"]
    }
    with pytest.raises(ValidationError):
        EnvironmentDiagnosis.model_validate(data)


def test_diagnosis_patch_is_optional():
    data = {
        "root_cause": "Missing env var",
        "proposed_fix": "Set DATABASE_URL in .env",
    }
    diag = EnvironmentDiagnosis.model_validate(data)
    assert diag.patch is None


def test_diagnosis_confidence_defaults_to_medium():
    data = {
        "root_cause": "Missing env var",
        "proposed_fix": "Set DATABASE_URL in .env",
    }
    diag = EnvironmentDiagnosis.model_validate(data)
    assert diag.confidence == "medium"
