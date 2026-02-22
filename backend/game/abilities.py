"""
abilities.py — Reroll, Flee, and Double-down logic.  
Each function mutates nothing directly; callers apply returned data to GameState.
"""

from __future__ import annotations
import random
from backend.game.map_builder import Chamber, QuestionSlot, reroll_chamber
from backend.config import HP_LOSS_WRONG, XP_PER_LEVEL


# ── Reroll ────────────────────────────────────────────────────────────────────

def do_reroll(
    chamber: Chamber,
    remaining_pool: list[QuestionSlot],
    answered_ids: set[str],
    abilities_remaining: dict[str, int],
    rng: random.Random,
) -> tuple[Chamber, list[QuestionSlot], dict[str, int], str]:
    """
    Swap the 4 doors in *chamber* for fresh ones.
    Returns (updated_chamber, updated_pool, updated_abilities, error_msg).
    """
    if abilities_remaining["reroll"] <= 0:
        return chamber, remaining_pool, abilities_remaining, "No Rerolls remaining."
    updated = dict(abilities_remaining)
    updated["reroll"] -= 1
    chamber, leftover = reroll_chamber(chamber, remaining_pool, answered_ids, rng)
    return chamber, leftover, updated, ""


# ── Flee ─────────────────────────────────────────────────────────────────────

def do_flee(
    abilities_remaining: dict[str, int],
) -> tuple[dict[str, int], str]:
    """
    Mark flee used.  The chamber stays unchanged (caller re-presents it).
    Returns (updated_abilities, error_msg).
    """
    if abilities_remaining["flee"] <= 0:
        return abilities_remaining, "No Flees remaining."
    updated = dict(abilities_remaining)
    updated["flee"] -= 1
    return updated, ""


# ── Double-down ───────────────────────────────────────────────────────────────

def resolve_double_down(
    is_correct: bool,
    level: int,
    hp: int,
    xp: int,
    abilities_remaining: dict[str, int],
) -> tuple[int, int, dict[str, int], int, int, str]:
    """
    Apply double-down outcome.
    Returns (new_hp, new_xp, updated_abilities, hp_delta, xp_delta, error_msg).
    """
    if abilities_remaining["double_down"] <= 0:
        return hp, xp, abilities_remaining, 0, 0, "No Double-downs remaining."
    updated = dict(abilities_remaining)
    updated["double_down"] -= 1
    base_xp = XP_PER_LEVEL.get(level, 1)
    if is_correct:
        xp_delta = base_xp * 2
        hp_delta = 0
        return hp, xp + xp_delta, updated, hp_delta, xp_delta, ""
    else:
        hp_delta = -HP_LOSS_WRONG * 2
        xp_delta = 0
        return max(0, hp + hp_delta), xp, updated, hp_delta, xp_delta, ""
