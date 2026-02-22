"""
gemini_client.py — Gemini Flash wrapper used exclusively for context summarisation.
"""

from __future__ import annotations
import google.generativeai as genai
from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.llm.prompts import build_summarise_prompt


def summarise(history_text: str) -> str:
    """
    Condense a chat history string into a short paragraph using Gemini Flash.
    Falls back gracefully if the API key is not configured.
    """
    if not GEMINI_API_KEY:
        # Soft fallback: truncate to last 500 chars with a note
        tail = history_text[-500:] if len(history_text) > 500 else history_text
        return f"[Summary unavailable — no GEMINI_API_KEY set]\n{tail}"

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = build_summarise_prompt(history_text)
    response = model.generate_content(prompt)
    return response.text.strip()
