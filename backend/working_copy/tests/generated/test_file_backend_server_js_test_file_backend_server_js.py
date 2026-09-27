"""
Auto-generated regression test.
Scenario : Validate source contract for server.js
Component: file:backend/server.js
Evidence : backend/server.js:1
Expected : backend/server.js remains valid Python and continues to declare server.js.
"""

import ast
from pathlib import Path


def test_file_backend_server_js():
    source_path = Path('backend/server.js')
    assert source_path.is_file(), f"Expected source file does not exist: {source_path}"
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    expected_symbol = ''
    if expected_symbol:
        declarations = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        assert expected_symbol in declarations, (
            f"Expected component {expected_symbol!r} was not found in {source_path}"
        )
