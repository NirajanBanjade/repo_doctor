"""
app/services/repo_importer.py

Stack detection for the Repository X-Ray feature.
See docs/features/01-repository-xray.md §Technical Implementation.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_PYTHON_MARKERS = ("pyproject.toml", "setup.py", "requirements.txt")
_NODE_MARKERS = ("package.json",)

_FRAMEWORK_IMPORTS = {
    "fastapi": "fastapi",
    "flask": "flask",
    "django": "django",
}

_TEST_RUNNERS = {
    "pytest": "pytest",
    "unittest": "unittest",
    "jest": "jest",
}


def detect_stack(repo_path: str) -> dict:
    """
    Returns {"language", "framework", "test_runner", "adapter_available"}.
    """
    language = _detect_language(repo_path)
    framework = _detect_framework(repo_path, language)
    test_runner = _detect_test_runner(repo_path, language)
    adapter_available = language in ("python",)

    if language == "unknown":
        logger.warning("repo_importer: could not detect language for %s", repo_path)

    return {
        "language": language,
        "framework": framework,
        "test_runner": test_runner,
        "adapter_available": adapter_available,
    }


def _detect_language(repo_path: str) -> str:
    for marker in _PYTHON_MARKERS:
        if os.path.exists(os.path.join(repo_path, marker)):
            return "python"
    for marker in _NODE_MARKERS:
        if os.path.exists(os.path.join(repo_path, marker)):
            return "typescript"
    return "unknown"


def _detect_framework(repo_path: str, language: str) -> str | None:
    if language != "python":
        return None
    # Scan entry point candidates for framework imports
    candidates = ["main.py", "app.py", "app/main.py", "app/__init__.py"]
    for candidate in candidates:
        fpath = os.path.join(repo_path, candidate)
        if not os.path.exists(fpath):
            continue
        try:
            with open(fpath) as fh:
                text = fh.read().lower()
            for keyword, name in _FRAMEWORK_IMPORTS.items():
                if f"import {keyword}" in text or f"from {keyword}" in text:
                    return name
        except OSError:
            continue
    return None


def _detect_test_runner(repo_path: str, language: str) -> str | None:
    if language == "python":
        # Check pyproject.toml / setup.cfg / requirements
        for fname in ("pyproject.toml", "requirements.txt", "requirements-dev.txt"):
            fpath = os.path.join(repo_path, fname)
            if not os.path.exists(fpath):
                continue
            try:
                with open(fpath) as fh:
                    text = fh.read().lower()
                if "pytest" in text:
                    return "pytest"
            except OSError:
                continue
        if os.path.isdir(os.path.join(repo_path, "tests")):
            return "pytest"
    if language == "typescript":
        pkg = os.path.join(repo_path, "package.json")
        if os.path.exists(pkg):
            try:
                import json

                with open(pkg) as fh:
                    data = json.load(fh)
                deps = {
                    **data.get("dependencies", {}),
                    **data.get("devDependencies", {}),
                }
                if "jest" in deps:
                    return "jest"
            except (OSError, ValueError, KeyError):
                pass
    return None
