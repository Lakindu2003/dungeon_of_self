"""
gemini_client.py — Single LLM client for the entire project (Gemini 3.0 Flash).

All strategy decisions, answer generation, reflection, and context summarisation
go through call().  Web search is Gemini's native Google Search grounding tool:
it activates within the same API call when use_web_search=True, consuming no
extra call from the LLM budget.  It must be False unless tool_web is active.
"""

from __future__ import annotations
from google import genai
from google.genai import types
from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.llm.prompts import SYSTEM_PROMPT, build_summarise_prompt

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in .env")
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def call(
    messages: list[dict[str, str]],
    use_web_search: bool = False,
    temperature: float = 0.7,
    system: str | None = None,
) -> str:
    """
    Send a generation request to Gemini 3.0 Flash.

    use_web_search=True attaches Gemini's built-in Google Search grounding tool.
    This must only be True when the agent has the tool_web skill active —
    it is False by default and controlled exclusively by the caller.

    Role mapping: "assistant" → "model" for Gemini's API convention.
    Returns the response text.
    """
    client = _get_client()
    resolved_system = system or SYSTEM_PROMPT

    contents: list[types.Content] = []
    for m in messages:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part(text=m["content"])])
        )

    tools = [types.Tool(google_search=types.GoogleSearch())] if use_web_search else None

    config = types.GenerateContentConfig(
        system_instruction=resolved_system,
        temperature=temperature,
        tools=tools,
    )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=config,
    )
    return response.text or ""


def summarise(history_text: str) -> str:
    """Condense chat history into a short paragraph (used by ctx_summarise skill)."""
    if not GEMINI_API_KEY:
        tail = history_text[-500:] if len(history_text) > 500 else history_text
        return f"[Summary unavailable — no GEMINI_API_KEY set]\n{tail}"

    client = _get_client()
    prompt = build_summarise_prompt(history_text)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )
    return response.text.strip() if response.text else history_text[-500:]
