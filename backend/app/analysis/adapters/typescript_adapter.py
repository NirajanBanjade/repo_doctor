"""
app/analysis/adapters/typescript_adapter.py

TypeScript language adapter stub.
MVP: returns empty lists with a logged warning. Never raises.
See ARCHITECTURE.md §4 and AGENTS.md §7.
"""

from __future__ import annotations

import logging

from app.analysis.base_adapter import AdapterBase, GraphEdge, GraphNode

logger = logging.getLogger(__name__)


class TypeScriptAdapter(AdapterBase):
    def detect(self, repo_path: str) -> bool:
        import os

        return os.path.exists(os.path.join(repo_path, "package.json"))

    def extract_nodes(self, repo_path: str) -> list[GraphNode]:
        logger.warning(
            "TypeScript adapter is a stub for MVP. " "No nodes extracted from %s.",
            repo_path,
        )
        return []

    def extract_edges(self, repo_path: str) -> list[GraphEdge]:
        return []
