"""
app/analysis/adapter_registry.py

Maps a detected language to the appropriate AdapterBase subclass.
See ARCHITECTURE.md §4.
"""
from __future__ import annotations

from app.analysis.base_adapter import AdapterBase
from app.analysis.adapters.typescript_adapter import TypeScriptAdapter

# Register adapters in priority order.
# Python adapter omitted until implementation is complete (stub raises).
_REGISTRY: list[type[AdapterBase]] = [
    TypeScriptAdapter,
    # PythonAdapter,  # uncomment when python_adapter.py is implemented
]


def get_adapter(repo_path: str) -> AdapterBase | None:
    """
    Return the first adapter whose detect() returns True for repo_path.
    Returns None if no adapter matches; callers must handle the no-adapter case.
    """
    for cls in _REGISTRY:
        adapter = cls()
        if adapter.detect(repo_path):
            return adapter
    return None
