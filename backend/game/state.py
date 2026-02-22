"""
state.py — GameState dataclass: single source of truth during a run.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import time


@dataclass
class GameState:
    # ── Identity ──────────────────────────────────────────────────────────────
    run_id: str = ""
    run_folder: str = ""

    # ── Progress ──────────────────────────────────────────────────────────────
    chamber_index: int = 0          # which chamber we are IN right now
    max_chambers: int = 20
    total_chambers: int = 0         # set by map_builder after loading

    # ── Resources ─────────────────────────────────────────────────────────────
    hp: int = 100
    xp: int = 0
    skill_points: int = 0
    xp_threshold_index: int = 0     # index into SKILL_POINT_XP_THRESHOLDS
    xp_next_threshold: int = 0      # absolute XP needed for next SP

    # ── Skills ────────────────────────────────────────────────────────────────
    active_skills: list[str] = field(default_factory=list)

    # ── Abilities ─────────────────────────────────────────────────────────────
    abilities_remaining: dict[str, int] = field(default_factory=lambda: {
        "reroll": 3,
        "flee": 3,
        "double_down": 3,
    })

    # ── Question tracking ─────────────────────────────────────────────────────
    answered_ids: list[str] = field(default_factory=list)  # all answered question IDs

    # ── Context / memory ──────────────────────────────────────────────────────
    chat_history: list[dict[str, str]] = field(default_factory=list)
    memory_store: dict[str, Any] = field(default_factory=dict)
    summarise_counter: int = 0      # exchanges since last Gemini summarise

    # ── Session stats ─────────────────────────────────────────────────────────
    correct_count: int = 0
    wrong_count: int = 0
    rooms_visited: int = 0
    skills_unlocked_count: int = 0

    # ── Status ────────────────────────────────────────────────────────────────
    status: str = "running"         # "running" | "won" | "dead"
    started_at: float = field(default_factory=time.time)

    # ── Double-down flag ──────────────────────────────────────────────────────
    double_down_active: bool = False

    def to_dict(self) -> dict:
        """Compact serialisation for SSE streaming to the frontend."""
        return {
            "run_id": self.run_id,
            "chamber_index": self.chamber_index,
            "max_chambers": self.max_chambers,
            "total_chambers": self.total_chambers,
            "hp": self.hp,
            "xp": self.xp,
            "skill_points": self.skill_points,
            "xp_next_threshold": self.xp_next_threshold,
            "active_skills": self.active_skills,
            "abilities_remaining": self.abilities_remaining,
            "correct_count": self.correct_count,
            "wrong_count": self.wrong_count,
            "rooms_visited": self.rooms_visited,
            "skills_unlocked_count": self.skills_unlocked_count,
            "status": self.status,
            "double_down_active": self.double_down_active,
        }
