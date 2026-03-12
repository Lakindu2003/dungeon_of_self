"""
app.py — Standalone annotation server on port 5000.

Reads gaia_validation.csv, serves one question at a time via a web UI,
and persists task_id + category annotations to annotations.csv.

Run:
    python3 backend/data_annotator/app.py
    # or from inside data_annotator/:
    python3 app.py
"""

from __future__ import annotations

import csv
import json
import os
import threading
import webbrowser
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# ── Paths ─────────────────────────────────────────────────────────────────────

HERE = Path(__file__).parent
DATA_CSV = HERE.parent / "data" / "gaia_validation.csv"
CATEGORIES_JSON = HERE / "categories.json"
ANNOTATIONS_CSV = HERE / "annotations.csv"

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="GAIA Annotator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_questions() -> list[dict]:
    """Return all rows from gaia_validation.csv as dicts."""
    if not DATA_CSV.exists():
        raise FileNotFoundError(f"Validation CSV not found: {DATA_CSV}")
    rows = []
    with DATA_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            rows.append(
                {
                    "index": i,
                    "task_id": row["task_id"].strip(),
                    "question": row["Question"].strip(),
                    "level": int(row["Level"]) if row["Level"].strip() else 0,
                }
            )
    return rows


def _load_annotations() -> dict[str, str]:
    """Return {task_id: category} from annotations.csv (empty dict if file absent)."""
    if not ANNOTATIONS_CSV.exists():
        return {}
    result = {}
    with ANNOTATIONS_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            result[row["task_id"].strip()] = row["category"].strip()
    return result


def _save_annotation(task_id: str, category: str) -> None:
    """Upsert a single annotation into annotations.csv."""
    existing = _load_annotations()
    existing[task_id] = category

    file_exists = ANNOTATIONS_CSV.exists()
    with ANNOTATIONS_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["task_id", "category"])
        for tid, cat in existing.items():
            writer.writerow([tid, cat])


def _load_categories() -> list[str]:
    """Return category list from categories.json."""
    if not CATEGORIES_JSON.exists():
        return ["Other"]
    with CATEGORIES_JSON.open(encoding="utf-8") as f:
        data = json.load(f)
    return data.get("categories", ["Other"])


# ── API ───────────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
def root():
    html_path = HERE / "index.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.get("/api/questions")
def get_questions():
    return _load_questions()


@app.get("/api/annotations")
def get_annotations():
    return _load_annotations()


@app.get("/api/categories")
def get_categories():
    return _load_categories()


class AnnotateRequest(BaseModel):
    task_id: str
    category: str


@app.post("/api/annotate")
def annotate(req: AnnotateRequest):
    if not req.task_id.strip():
        raise HTTPException(status_code=400, detail="task_id must not be empty")
    if not req.category.strip():
        raise HTTPException(status_code=400, detail="category must not be empty")
    _save_annotation(req.task_id.strip(), req.category.strip())
    return {"ok": True}


# ── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"Source CSV  : {DATA_CSV}")
    print(f"Annotations : {ANNOTATIONS_CSV}")
    print(f"Categories  : {CATEGORIES_JSON}")

    # Open browser after a short delay to let uvicorn bind
    def _open_browser():
        import time
        time.sleep(1.2)
        webbrowser.open("http://localhost:5000")

    threading.Thread(target=_open_browser, daemon=True).start()
    uvicorn.run("app:app", host="0.0.0.0", port=5000, reload=True, app_dir=str(HERE))
