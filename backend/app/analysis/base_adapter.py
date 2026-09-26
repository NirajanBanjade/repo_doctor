"""
app/analysis/base_adapter.py

Abstract interface that all language adapters must implement.
See ARCHITECTURE.md §4 and AGENTS.md §7 for conventions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GraphNode:
    node_id: str
    kind: str  # "function" | "class" | "module" | "file"
    name: str
    path: str
    line_start: int
    line_end: int
    language: str
    summary: str | None = None
    key_module: bool = False


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relationship: str  # "calls" | "imports" | "inherits" | "uses"
    file: str
    line: int
    evidence_status: str = "confirmed_static"  # | "observed_test" | "inferred"
    note: str | None = None


class AdapterBase(ABC):
    """
    Base class for all language-specific repository adapters.

    Subclasses must be stateless and deterministic:
    same source tree → same output every run.
    Adapters must not make network calls, spawn containers, or call Bob.
    """

    @abstractmethod
    def detect(self, repo_path: str) -> bool:
        """
        Return True if this adapter should process the given repository.
        Must be fast: file-system checks only, no parsing.
        """

    @abstractmethod
    def extract_nodes(self, repo_path: str) -> list[GraphNode]:
        """
        Return all code entities found in the repository.
        Dynamic constructs that cannot be statically resolved must be
        returned with evidence_status="inferred" on the corresponding edge.
        """

    @abstractmethod
    def extract_edges(self, repo_path: str) -> list[GraphEdge]:
        """
        Return all directed dependency relationships found in the repository.
        source_id → target_id means "source depends on target".
        """
