"""
Sample fixture Python file used by X-Ray unit tests.
Contains: a class with inheritance, functions, imports, and a dynamic call.
"""

from __future__ import annotations

from typing import Any


class Base:
    def method_a(self) -> str:
        return "base"


class Child(Base):
    def method_b(self) -> int:
        return 42

    def dynamic_example(self) -> Any:
        # This should produce an inferred edge
        return self.method_a()


def standalone_function(x: int, y: int) -> int:
    return x + y


async def async_handler() -> dict:
    return {"status": "ok"}
