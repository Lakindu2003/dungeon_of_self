"""
memory.py — Simple key-value memory store helpers.
The LLM stores facts with <memory_store> tags; the full store is
injected as context on every subsequent answer call.
"""

from __future__ import annotations
from typing import Any


def format_memory_block(memory_store: dict[str, Any]) -> str:
    """Format the memory store as a readable context block."""
    if not memory_store:
        return ""
    lines = [f"  {k}: {v}" for k, v in memory_store.items()]
    return "Your stored memory:\n" + "\n".join(lines)


def apply_memory_store(memory_store: dict[str, Any], key: str, value: Any) -> dict[str, Any]:
    """Return a new memory store dict with the key-value pair added."""
    updated = dict(memory_store)
    updated[key] = value
    return updated
