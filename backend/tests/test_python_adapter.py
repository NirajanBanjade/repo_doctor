"""
tests/test_python_adapter.py

Unit tests for PythonAdapter: node extraction, edge extraction,
syntax-error tolerance, and dynamic-call inferred edges.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import textwrap

from app.analysis.adapters.python_adapter import PythonAdapter

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# ── Helpers ───────────────────────────────────────────────────────────────────


def make_repo(files: dict[str, str]) -> str:
    """Create a temp dir with the given file contents. Caller must clean up."""
    d = tempfile.mkdtemp()
    for name, content in files.items():
        path = os.path.join(d, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(textwrap.dedent(content))
    # Add a requirements.txt so detect() returns True
    with open(os.path.join(d, "requirements.txt"), "w") as fh:
        fh.write("fastapi\n")
    return d


# ── detect() ─────────────────────────────────────────────────────────────────


def test_detect_true_with_requirements(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    assert PythonAdapter().detect(str(tmp_path)) is True


def test_detect_true_with_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[build-system]\n")
    assert PythonAdapter().detect(str(tmp_path)) is True


def test_detect_false_empty_dir(tmp_path):
    assert PythonAdapter().detect(str(tmp_path)) is False


def test_detect_true_with_py_file(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n")
    assert PythonAdapter().detect(str(tmp_path)) is True


# ── extract_nodes() ───────────────────────────────────────────────────────────


def test_extract_nodes_from_fixture():
    adapter = PythonAdapter()
    nodes = adapter.extract_nodes(FIXTURE_DIR)
    node_kinds = {n.kind for n in nodes}
    node_names = {n.name for n in nodes}

    assert "module" in node_kinds
    assert "class" in node_kinds
    assert "function" in node_kinds
    assert "Base" in node_names
    assert "Child" in node_names
    assert "standalone_function" in node_names
    assert "async_handler" in node_names


def test_extract_nodes_has_correct_language():
    nodes = PythonAdapter().extract_nodes(FIXTURE_DIR)
    for n in nodes:
        assert n.language == "python"


def test_extract_nodes_line_range_populated():
    nodes = PythonAdapter().extract_nodes(FIXTURE_DIR)
    for n in nodes:
        assert n.line_start >= 1
        assert n.line_end >= n.line_start


def test_extract_nodes_node_id_format():
    nodes = PythonAdapter().extract_nodes(FIXTURE_DIR)
    for n in nodes:
        assert n.node_id  # non-empty


def test_extract_nodes_skips_syntax_error_file():
    """Syntax error in one file must not abort the run; other files still parsed."""
    d = make_repo(
        {
            "good.py": "def foo(): return 1\n",
            "bad.py": "def broken(:\n    pass\n",  # syntax error
        }
    )
    try:
        nodes = PythonAdapter().extract_nodes(d)
        names = {n.name for n in nodes}
        assert "foo" in names  # good file parsed
    finally:
        shutil.rmtree(d)


def test_extract_nodes_empty_repo():
    d = make_repo({"empty.py": ""})
    try:
        nodes = PythonAdapter().extract_nodes(d)
        # Should get a module node for empty.py at minimum
        assert any(n.kind == "module" for n in nodes)
    finally:
        shutil.rmtree(d)


def test_extract_nodes_nested_classes_and_functions():
    d = make_repo({"nested.py": """
        class Outer:
            class Inner:
                pass
            def method(self): pass
    """})
    try:
        nodes = PythonAdapter().extract_nodes(d)
        names = {n.name for n in nodes}
        assert "Outer" in names
        assert "Inner" in names
        assert "method" in names
    finally:
        shutil.rmtree(d)


# ── extract_edges() ───────────────────────────────────────────────────────────


def test_extract_edges_import_edge():
    d = make_repo({"importer.py": "import os\nimport sys\n"})
    try:
        edges = PythonAdapter().extract_edges(d)
        rels = {e.relationship for e in edges}
        assert "imports" in rels
        statuses = {e.evidence_status for e in edges}
        assert "confirmed_static" in statuses
    finally:
        shutil.rmtree(d)


def test_extract_edges_from_import():
    d = make_repo({"mod.py": "from os.path import join\n"})
    try:
        edges = PythonAdapter().extract_edges(d)
        assert any(e.relationship == "imports" for e in edges)
    finally:
        shutil.rmtree(d)


def test_extract_edges_inheritance():
    d = make_repo({"classes.py": "class Child(Base): pass\n"})
    try:
        edges = PythonAdapter().extract_edges(d)
        inherit = [e for e in edges if e.relationship == "inherits"]
        assert len(inherit) >= 1
        assert inherit[0].evidence_status == "confirmed_static"
        assert inherit[0].target_id == "Base"
    finally:
        shutil.rmtree(d)


def test_extract_edges_dynamic_call_inferred():
    d = make_repo({"dyn.py": "def f(obj): return getattr(obj, 'x')\n"})
    try:
        edges = PythonAdapter().extract_edges(d)
        inferred = [e for e in edges if e.evidence_status == "inferred"]
        assert len(inferred) >= 1
        assert inferred[0].note is not None
    finally:
        shutil.rmtree(d)


def test_extract_edges_all_have_file_and_line():
    edges = PythonAdapter().extract_edges(FIXTURE_DIR)
    for e in edges:
        assert e.file, f"edge missing file: {e}"
        assert e.line >= 1, f"edge line < 1: {e}"


def test_extract_edges_syntax_error_file_skipped():
    """Edges from good files are still returned when one file has a syntax error."""
    d = make_repo(
        {
            "good.py": "import os\n",
            "bad.py": "def broken(:\n    pass\n",
        }
    )
    try:
        edges = PythonAdapter().extract_edges(d)
        assert any(e.relationship == "imports" for e in edges)
    finally:
        shutil.rmtree(d)


def test_extract_edges_no_py_files():
    d = tempfile.mkdtemp()
    try:
        edges = PythonAdapter().extract_edges(d)
        assert edges == []
    finally:
        shutil.rmtree(d)
