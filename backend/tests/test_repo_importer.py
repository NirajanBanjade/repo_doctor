"""
tests/test_repo_importer.py

Unit tests for stack detection (repo_importer.detect_stack).
"""

from __future__ import annotations

import json

from app.services.repo_importer import detect_stack


def test_python_via_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\npytest\n")
    stack = detect_stack(str(tmp_path))
    assert stack["language"] == "python"
    assert stack["adapter_available"] is True


def test_python_via_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[tool.pytest.ini_options]\n")
    stack = detect_stack(str(tmp_path))
    assert stack["language"] == "python"


def test_python_via_setup_py(tmp_path):
    (tmp_path / "setup.py").write_text("from setuptools import setup\n")
    stack = detect_stack(str(tmp_path))
    assert stack["language"] == "python"


def test_typescript_via_package_json(tmp_path):
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "app", "dependencies": {}})
    )
    stack = detect_stack(str(tmp_path))
    assert stack["language"] == "typescript"
    assert stack["adapter_available"] is False


def test_unknown_language(tmp_path):
    stack = detect_stack(str(tmp_path))
    assert stack["language"] == "unknown"
    assert stack["adapter_available"] is False


def test_fastapi_framework_detected(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    stack = detect_stack(str(tmp_path))
    assert stack["framework"] == "fastapi"


def test_flask_framework_detected(tmp_path):
    (tmp_path / "requirements.txt").write_text("flask\n")
    (tmp_path / "app.py").write_text("from flask import Flask\napp = Flask(__name__)\n")
    stack = detect_stack(str(tmp_path))
    assert stack["framework"] == "flask"


def test_no_framework_returns_none(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests\n")
    (tmp_path / "main.py").write_text("print('hello')\n")
    stack = detect_stack(str(tmp_path))
    assert stack["framework"] is None


def test_pytest_test_runner_from_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("pytest>=7\nfastapi\n")
    stack = detect_stack(str(tmp_path))
    assert stack["test_runner"] == "pytest"


def test_pytest_detected_via_tests_dir(tmp_path):
    (tmp_path / "requirements.txt").write_text("requests\n")
    (tmp_path / "tests").mkdir()
    stack = detect_stack(str(tmp_path))
    assert stack["test_runner"] == "pytest"


def test_jest_detected_via_package_json(tmp_path):
    pkg = {"name": "app", "devDependencies": {"jest": "^29.0.0"}}
    (tmp_path / "package.json").write_text(json.dumps(pkg))
    stack = detect_stack(str(tmp_path))
    assert stack["test_runner"] == "jest"


def test_python_takes_priority_over_node(tmp_path):
    """If both requirements.txt and package.json exist, Python wins."""
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    (tmp_path / "package.json").write_text("{}")
    stack = detect_stack(str(tmp_path))
    assert stack["language"] == "python"
