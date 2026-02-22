"""
calculator.py — Sandboxed Python expression evaluator.
The LLM emits <tool_call>{"type":"calculator","expr":"EXPRESSION"}</tool_call>
and this module evaluates it safely.
"""

from __future__ import annotations
import math
import re

# Safe namespace: basic math functions only
_SAFE_GLOBALS: dict = {
    "__builtins__": {},
    "abs": abs, "round": round, "min": min, "max": max,
    "sum": sum, "pow": pow, "int": int, "float": float,
    "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
    "log2": math.log2, "exp": math.exp,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e,
    "ceil": math.ceil, "floor": math.floor,
    "factorial": math.factorial,
}

# Block any attempt to access dunders or builtins
_BLOCKED = re.compile(r"__|\bimport\b|\bexec\b|\beval\b|\bopen\b|\bos\b|\bsys\b")


def evaluate(expr: str) -> str:
    """
    Evaluate a math expression string.
    Returns the result as a string, or an error message prefixed with 'ERROR:'.
    """
    if _BLOCKED.search(expr):
        return "ERROR: Expression contains forbidden keywords."
    try:
        result = eval(expr, _SAFE_GLOBALS, {})  # noqa: S307
        return str(result)
    except Exception as exc:
        return f"ERROR: {exc}"
