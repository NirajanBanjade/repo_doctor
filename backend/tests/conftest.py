"""
tests/conftest.py — shared test configuration.
"""

from __future__ import annotations

import pytest

from app.db import evidence_store


@pytest.fixture(autouse=True)
def isolate_db():
    """Reset the global engine so every test gets a clean DB."""
    evidence_store._engine = None
    yield
    evidence_store._engine = None
