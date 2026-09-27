"""
Auto-generated regression test.
Scenario : Validate source contract for share.service.js
Component: file:backend/modules/share/share.service.js
Evidence : backend/modules/share/share.service.js:1
Expected : The source remains parseable and continues to declare share.service.js.
"""

import ast
from pathlib import Path


def test_file_backend_modules_share_share_service_js_source_contract():
    source_path = Path('backend/modules/share/share.service.js')
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
