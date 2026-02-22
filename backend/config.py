"""
config.py — Single source of truth for all tunable constants.
Change values here; everything else imports from this file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Run limits ────────────────────────────────────────────────────────────────
MAX_CHAMBERS: int = int(os.getenv("MAX_CHAMBERS", "20"))

# ── HP / XP ───────────────────────────────────────────────────────────────────
STARTING_HP: int = 100
HP_LOSS_WRONG: int = 20          # flat loss per wrong answer (doubled by double-down)

# XP awarded per GAIA question level
XP_PER_LEVEL: dict[int, int] = {1: 1, 2: 2, 3: 3}

# Incremental XP needed to earn the NEXT skill-point.
# e.g. first SP at cumulative 1 XP, second SP at cumulative 1+2=3 XP, etc.
SKILL_POINT_XP_THRESHOLDS: list[int] = [1, 2, 4, 8, 16]

# ── Skill costs (in Skill Points) ─────────────────────────────────────────────
SKILL_COSTS: dict[str, int] = {
    # Prompt Engineering (sequential)
    "pe_cot":       1,
    "pe_plan":      1,
    "pe_reflect":   1,
    # Context (sequential)
    "ctx_enough":   1,
    "ctx_overload": 1,
    "ctx_summarise":1,
    # Tools (parallel)
    "tool_calc":    2,
    "tool_web":     3,
    "tool_memory":  2,
}

# ── Abilities ─────────────────────────────────────────────────────────────────
REROLL_USES: int = 3
FLEE_USES: int = 3
DOUBLE_DOWN_USES: int = 3

# ── Dungeon map ───────────────────────────────────────────────────────────────
DOORS_PER_CHAMBER: int = 4

# ── Context window management ─────────────────────────────────────────────────
CONTEXT_HISTORY_SIZE: int = 5          # messages kept for ctx_enough
CONTEXT_SUMMARISE_EVERY: int = 10      # exchanges before Gemini summarises

# ── LLM providers ─────────────────────────────────────────────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str    = os.getenv("OLLAMA_MODEL", "llama3")

GEMINI_API_KEY: str  = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str    = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

TAVILY_API_KEY: str  = os.getenv("TAVILY_API_KEY", "")
TAVILY_MAX_RESULTS: int = 3   # number of web pages fetched
