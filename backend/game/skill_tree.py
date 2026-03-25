"""
skill_tree.py — Skill definitions, prerequisites, costs, and unlock logic.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from backend.config import SKILL_COSTS


@dataclass
class Skill:
    id: str
    name: str
    category: str           # "prompt_engineering" | "context" | "tools"
    description: str
    requires: Optional[str] = None   # skill ID that must be owned first (None = free)
    cost: int = 1


SKILL_TREE: dict[str, Skill] = {
    # ── Prompt Engineering (sequential) ──────────────────────────────────────
    "pe_cot": Skill(
        id="pe_cot",
        name="CoT",
        category="prompt_engineering",
        description="Appends a chain-of-thought instruction to the answer prompt.",
        requires=None,
        cost=SKILL_COSTS["pe_cot"],
    ),
    "pe_plan": Skill(
        id="pe_plan",
        name="Plan+Reflect",
        category="prompt_engineering",
        description="Prepends a planning block: outline approach before answering.",
        requires="pe_cot",
        cost=SKILL_COSTS["pe_plan"],
    ),
    "pe_reflect": Skill(
        id="pe_reflect",
        name="Reflection++",
        category="prompt_engineering",
        description="Adds a second dedicated reflection LLM call after the first answer.",
        requires="pe_plan",
        cost=SKILL_COSTS["pe_reflect"],
    ),
    # ── Context (sequential) ─────────────────────────────────────────────────
    "ctx_enough": Skill(
        id="ctx_enough",
        name="Enough",
        category="context",
        description=f"Includes the last 5 Q&A pairs in the message history.",
        requires=None,
        cost=SKILL_COSTS["ctx_enough"],
    ),
    "ctx_overload": Skill(
        id="ctx_overload",
        name="Overload",
        category="context",
        description="Full chat history included in every call.",
        requires="ctx_enough",
        cost=SKILL_COSTS["ctx_overload"],
    ),
    "ctx_summarise": Skill(
        id="ctx_summarise",
        name="Summariser",
        category="context",
        description="Periodically summarises old history via Gemini Flash.",
        requires="ctx_overload",
        cost=SKILL_COSTS["ctx_summarise"],
    ),
    # ── Tools (parallel) ─────────────────────────────────────────────────────
    "tool_calc": Skill(
        id="tool_calc",
        name="Calc",
        category="tools",
        description="Python calculator: LLM can evaluate mathematical expressions.",
        requires=None,
        cost=SKILL_COSTS["tool_calc"],
    ),
    "tool_web": Skill(
        id="tool_web",
        name="Search",
        category="tools",
        description="Enables Gemini native Google Search grounding on the answer call (no extra call).",
        requires=None,
        cost=SKILL_COSTS["tool_web"],
    ),
    "tool_memory": Skill(
        id="tool_memory",
        name="Memory",
        category="tools",
        description="LLM can store key-value pairs; full memory injected as context.",
        requires=None,
        cost=SKILL_COSTS["tool_memory"],
    ),
}


def get_available_unlocks(active_skills: list[str], skill_points: int) -> list[Skill]:
    """Return skills the LLM can afford and has prerequisites for."""
    available = []
    for skill in SKILL_TREE.values():
        if skill.id in active_skills:
            continue                          # already owned
        if skill.cost > skill_points:
            continue                          # can't afford
        if skill.requires and skill.requires not in active_skills:
            continue                          # missing prerequisite
        available.append(skill)
    return available


def apply_unlock(skill_id: str, active_skills: list[str], skill_points: int) -> tuple[list[str], int, str]:
    """
    Validate and apply a skill unlock.
    Returns (updated_active_skills, updated_skill_points, error_message).
    error_message is empty string on success.
    """
    if skill_id not in SKILL_TREE:
        return active_skills, skill_points, f"Unknown skill: {skill_id}"
    skill = SKILL_TREE[skill_id]
    if skill_id in active_skills:
        return active_skills, skill_points, f"Skill {skill_id} already owned."
    if skill.requires and skill.requires not in active_skills:
        return active_skills, skill_points, f"Prerequisite {skill.requires} not met."
    if skill.cost > skill_points:
        return active_skills, skill_points, f"Not enough SP ({skill_points} < {skill.cost})."
    return active_skills + [skill_id], skill_points - skill.cost, ""


def describe_skill_for_prompt(skill: Skill) -> str:
    prereq = f" (requires {skill.requires})" if skill.requires else ""
    return f"  - {skill.id}: {skill.name} — {skill.description} Cost: {skill.cost} SP{prereq}"
