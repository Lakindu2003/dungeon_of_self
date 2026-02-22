"""
scorer.py — Answer evaluation with normalisation.
"""

from __future__ import annotations
import re
import unicodedata


def _normalise(text: str) -> str:
    """Lowercase, strip accents, remove punctuation, collapse whitespace."""
    text = text.strip().lower()
    # Decompose unicode and drop combining marks
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    # Remove punctuation except decimal points and forward slashes (fractions)
    text = re.sub(r"[^\w\s./]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _numeric_equal(a: str, b: str) -> bool:
    """Check whether two strings represent the same number."""
    try:
        return abs(float(a) - float(b)) < 1e-6
    except ValueError:
        return False


def check_answer(llm_answer: str, correct_answer: str) -> tuple[bool, str, str]:
    """
    Compare the LLM answer against the correct answer.
    Returns (is_correct, normalised_llm, normalised_correct).
    """
    norm_llm = _normalise(llm_answer)
    norm_correct = _normalise(correct_answer)

    if norm_llm == norm_correct:
        return True, norm_llm, norm_correct
    if _numeric_equal(norm_llm, norm_correct):
        return True, norm_llm, norm_correct
    # Substring containment (e.g. "willam shakespeare" inside long answer)
    if norm_correct in norm_llm or norm_llm in norm_correct:
        return True, norm_llm, norm_correct
    return False, norm_llm, norm_correct
