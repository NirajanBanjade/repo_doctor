"""Tests for the JavaScript and TypeScript repository adapter."""

from __future__ import annotations

from app.analysis.adapters.typescript_adapter import TypeScriptAdapter


def test_extracts_files_classes_functions_and_imports(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "main.ts").write_text(
        "import { helper } from './utils';\n"
        "export class App {}\n"
        "export function start() { return helper(); }\n"
    )
    (tmp_path / "utils.ts").write_text("export const helper = () => true;\n")

    adapter = TypeScriptAdapter()
    nodes = adapter.extract_nodes(str(tmp_path))
    edges = adapter.extract_edges(str(tmp_path))

    assert adapter.detect(str(tmp_path)) is True
    assert {node.name for node in nodes} >= {
        "main.ts",
        "App",
        "start",
        "utils.ts",
        "helper",
    }
    assert any(
        edge.source_id == "main.ts"
        and edge.target_id == "utils.ts"
        and edge.evidence_status == "confirmed_static"
        for edge in edges
    )


def test_external_imports_are_inferred(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "main.js").write_text("const express = require('express');\n")

    edges = TypeScriptAdapter().extract_edges(str(tmp_path))

    assert len(edges) == 1
    assert edges[0].target_id == "external::express"
    assert edges[0].evidence_status == "inferred"
    assert edges[0].note is not None
