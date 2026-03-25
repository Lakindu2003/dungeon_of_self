"""
map_builder.py — Loads GAIA CSV, builds Chamber objects for the dungeon.
"""

from __future__ import annotations
import csv
import random
from dataclasses import dataclass, field
from pathlib import Path


DATA_PATH = Path(__file__).parent.parent / "data" / "gaia_validation_annotated.csv"


@dataclass
class QuestionSlot:
    task_id: str
    question: str
    level: int
    final_answer: str
    category: str
    # metadata kept for logging but not shown to LLM
    file_name: str = ""
    annotator_metadata: str = ""


@dataclass
class Chamber:
    index: int
    doors: list[QuestionSlot] = field(default_factory=list)   # exactly 4 slots
    visited_door_ids: set[str] = field(default_factory=set)


def load_questions(csv_path: Path = DATA_PATH) -> list[QuestionSlot]:
    """Load all questions from CSV; skip rows with file attachments."""
    questions: list[QuestionSlot] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("file_name", "").strip():
                continue   # skip file-attachment questions
            questions.append(QuestionSlot(
                task_id=row["task_id"].strip(),
                question=row["Question"].strip(),
                level=int(row["Level"]),
                final_answer=row["Final answer"].strip(),
                category=row.get("category", "General").strip(),
                file_name=row.get("file_name", ""),
                annotator_metadata=row.get("Annotator Metadata", ""),
            ))
    return questions


def build_chambers(questions: list[QuestionSlot], seed: int = 42) -> list[Chamber]:
    """Shuffle questions and pack them into chambers of 4."""
    rng = random.Random(seed)
    shuffled = questions[:]
    rng.shuffle(shuffled)

    chambers: list[Chamber] = []
    for i in range(0, len(shuffled), 4):
        batch = shuffled[i: i + 4]
        if not batch:
            break
        chambers.append(Chamber(index=len(chambers), doors=batch))
    return chambers


def reroll_chamber(
    chamber: Chamber,
    remaining_pool: list[QuestionSlot],
    answered_ids: set[str],
    rng: random.Random,
) -> tuple[Chamber, list[QuestionSlot]]:
    """
    Replace the 4 doors of *chamber* with fresh ones from remaining_pool.
    Questions that have already been answered are never reused.
    Returns the updated chamber and the leftover pool.
    """
    available = [q for q in remaining_pool if q.task_id not in answered_ids]
    rng.shuffle(available)
    new_doors = available[:4]
    leftover = available[4:]
    # Put back old doors that haven't been answered yet
    old_unanswered = [
        d for d in chamber.doors if d.task_id not in answered_ids
    ]
    leftover = leftover + old_unanswered
    chamber.doors = new_doors
    return chamber, leftover
