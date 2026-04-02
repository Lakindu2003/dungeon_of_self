"""
run_logger.py — Structured logging for a single dungeon run.

Folder layout per run:
  logs/run_{timestamp}_{run_id}/
    full_run.json            — complete chronological event log (written at end)
    skill_unlocks.json       — order of unlocks + reasons + chat snippets
    skills_summary.json      — flat list of all unlocked skills
    incorrect_answers.json   — wrong Q&A with active tools + chat
    category_accuracy.json   — per-category accuracy breakdown
    ability_reroll.json      — each reroll: doors before/after, tools, reason
    ability_flee.json        — each flee: chamber, tools, chat, reason
    ability_double_down.json — each double-down: question, outcome, hp/xp, reason

All log files are appended as JSON arrays and written incrementally.
"""

from __future__ import annotations
import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Any


LOG_ROOT = Path(__file__).parent.parent.parent / "logs"


def extract_tag(text: str, tag: str) -> str:
    """Extract the content of the first matching XML tag. Returns '' if not found."""
    match = re.search(rf"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _append_json_array(path: Path, entry: dict) -> None:
    """Append an entry to a JSON array file (reads, appends, rewrites)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
    data.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


class RunLogger:
    def __init__(self, run_id: str, seed: int = None, mode: str = None):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = run_id
        if seed is not None and mode is not None:
            folder_path_str = str(LOG_ROOT / f"run_{seed}_{mode}_{ts}_{run_id}")
        else:
            folder_path_str = str(LOG_ROOT / f"run_{ts}_{run_id}")
        self.folder = Path(folder_path_str)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._events: list[dict] = []     # accumulates for full_run.json

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _event(self, event_type: str, data: dict) -> dict:
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            **data,
        }
        self._events.append(entry)
        return entry

    # ── Skill unlocks ─────────────────────────────────────────────────────────

    def log_skill_unlock(
        self,
        skill_id: str,
        skill_name: str,
        sp_cost: int,
        xp_at_time: int,
        hp_at_time: int,
        chamber_index: int,
        llm_raw_response: str,
        chat_history_snippet: list[dict],
    ) -> None:
        reason = extract_tag(llm_raw_response, "reason")
        entry = {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "sp_cost": sp_cost,
            "xp_at_time": xp_at_time,
            "hp_at_time": hp_at_time,
            "chamber_index": chamber_index,
            "reason": reason,
            "raw_response": llm_raw_response,
            "chat_history_snippet": chat_history_snippet[-6:],
        }
        _append_json_array(self.folder / "skill_unlocks.json", entry)
        _append_json_array(self.folder / "skills_summary.json", {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "chamber_index": chamber_index,
            "reason": reason,
        })
        self._event("skill_unlock", entry)

    # ── Incorrect answers ─────────────────────────────────────────────────────

    def log_wrong_answer(
        self,
        task_id: str,
        question: str,
        category: str,
        level: int,
        llm_answer: str,
        correct_answer: str,
        active_skills: list[str],
        chamber_index: int,
        chat_log_for_question: list[dict],
        llm_raw_response: str,
    ) -> None:
        entry = {
            "task_id": task_id,
            "question": question,
            "category": category,
            "level": level,
            "llm_answer": llm_answer,
            "correct_answer": correct_answer,
            "active_tools": [s for s in active_skills if s.startswith("tool_")],
            "active_skills": active_skills,
            "chamber_index": chamber_index,
            "chat_log_for_question": chat_log_for_question,
            "raw_response": llm_raw_response,
        }
        _append_json_array(self.folder / "incorrect_answers.json", entry)
        self._event("wrong_answer", entry)

    # ── Category accuracy ─────────────────────────────────────────────────────

    def update_category_accuracy(self, category_stats: dict[str, dict]) -> None:
        """Overwrite the category accuracy file with current stats."""
        _write_json(self.folder / "category_accuracy.json", category_stats)

    # ── Ability: Reroll ───────────────────────────────────────────────────────

    def log_reroll(
        self,
        chamber_index: int,
        doors_before: list[dict],
        doors_after: list[dict],
        active_skills: list[str],
        llm_raw_response: str,
    ) -> None:
        reason = extract_tag(llm_raw_response, "reason")
        entry = {
            "chamber_index": chamber_index,
            "doors_before": doors_before,   # list of {task_id, question, category, level}
            "doors_after": doors_after,
            "active_skills": active_skills,
            "active_tools": [s for s in active_skills if s.startswith("tool_")],
            "reason": reason,
            "raw_response": llm_raw_response,
        }
        _append_json_array(self.folder / "ability_reroll.json", entry)
        self._event("ability_reroll", entry)

    # ── Ability: Flee ─────────────────────────────────────────────────────────

    def log_flee(
        self,
        chamber_index: int,
        doors_available: list[dict],
        active_skills: list[str],
        chat_at_point: list[dict],
        llm_raw_response: str,
    ) -> None:
        reason = extract_tag(llm_raw_response, "reason")
        entry = {
            "chamber_index": chamber_index,
            "doors_available": doors_available,
            "active_skills": active_skills,
            "active_tools": [s for s in active_skills if s.startswith("tool_")],
            "chat_at_point": chat_at_point[-10:],
            "reason": reason,
            "raw_response": llm_raw_response,
        }
        _append_json_array(self.folder / "ability_flee.json", entry)
        self._event("ability_flee", entry)

    # ── Ability: Double-down ──────────────────────────────────────────────────

    def log_double_down(
        self,
        chamber_index: int,
        task_id: str,
        question: str,
        level: int,
        category: str,
        active_skills: list[str],
        outcome: str,   # "correct" | "wrong"
        hp_delta: int,
        xp_delta: int,
        chat_for_question: list[dict],
        llm_raw_response: str,
    ) -> None:
        reason = extract_tag(llm_raw_response, "reason")
        entry = {
            "chamber_index": chamber_index,
            "task_id": task_id,
            "question": question,
            "level": level,
            "category": category,
            "active_skills": active_skills,
            "active_tools": [s for s in active_skills if s.startswith("tool_")],
            "outcome": outcome,
            "hp_delta": hp_delta,
            "xp_delta": xp_delta,
            "chat_for_question": chat_for_question,
            "reason": reason,
            "raw_response": llm_raw_response,
        }
        _append_json_array(self.folder / "ability_double_down.json", entry)
        self._event("ability_double_down", entry)

    # ── Memory ───────────────────────────────────────────────────────────────

    def log_memory_store(self, chamber_index: int, memory_store: dict) -> None:
        if not memory_store:
            return
        entry = {
            "chamber_index": chamber_index,
            "memory_store": memory_store.copy()
        }
        _append_json_array(self.folder / "memory.json", entry)
        self._event("memory_log", entry)

    # ── Generic event (strategy calls, correct answers, etc.) ─────────────────

    def log_event(self, event_type: str, data: dict) -> None:
        self._event(event_type, data)

    # ── Finalise ──────────────────────────────────────────────────────────────

    def finalise(self, final_state_dict: dict, category_stats: dict) -> None:
        """Write full_run.json and ensure category_accuracy.json is up to date."""
        self.update_category_accuracy(category_stats)
        full = {
            "run_id": self.run_id,
            "final_state": final_state_dict,
            "events": self._events,
        }
        _write_json(self.folder / "full_run.json", full)

    @property
    def folder_path(self) -> str:
        return str(self.folder)
