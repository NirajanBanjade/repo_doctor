"""
app/analysis/adapter_registry.py

Maps a detected language to the appropriate AdapterBase subclass.
See ARCHITECTURE.md §4.
"""

from __future__ import annotations

from app.analysis.adapters.python_adapter import PythonAdapter
from app.analysis.adapters.typescript_adapter import TypeScriptAdapter
from app.analysis.base_adapter import AdapterBase

# Priority order: Python first (MVP), TypeScript stub second.
_REGISTRY: list[type[AdapterBase]] = [
    PythonAdapter,
    TypeScriptAdapter,
]


def get_adapter(language: str) -> AdapterBase | None:
    """
    Return adapter for the detected language, or None if unsupported.
    Falls back to detect() on each adapter for unknown languages.
    """
    _map = {"python": PythonAdapter, "typescript": TypeScriptAdapter}
    cls = _map.get(language)
    if cls:
        return cls()
    return None


def get_adapter_for_repo(repo_path: str) -> AdapterBase | None:
    """
    Return first adapter whose detect() returns True for repo_path.
    """
    for cls in _REGISTRY:
        adapter = cls()
        if adapter.detect(repo_path):
            return adapter
    return None
