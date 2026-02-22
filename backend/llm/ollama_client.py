"""
ollama_client.py — Thin wrapper around Ollama /api/chat.
"""

from __future__ import annotations
import httpx
from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from backend.llm.prompts import SYSTEM_PROMPT


def call(
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.7,
    system: str | None = None,
) -> str:
    """
    Send a chat completion request to Ollama.
    Returns the assistant message content string.
    """
    resolved_model = model or OLLAMA_MODEL
    resolved_system = system or SYSTEM_PROMPT

    payload = {
        "model": resolved_model,
        "stream": False,
        "options": {"temperature": temperature},
        "messages": [
            {"role": "system", "content": resolved_system},
            *messages,
        ],
    }
    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=180.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]
