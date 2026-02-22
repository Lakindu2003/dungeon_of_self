"""
main.py — FastAPI application.

Endpoints:
  POST /api/start           — start a new autonomous run
  GET  /api/stream/{run_id} — SSE stream of GameState + log events
  GET  /api/log/{run_id}    — download the finished run's folder path info
  GET  /                    — serves frontend/index.html
"""

from __future__ import annotations
import json
import queue
import threading
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from backend.llm.agent import run_agent
from backend.config import MAX_CHAMBERS, OLLAMA_MODEL

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

app = FastAPI(title="Dungeon of Self")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory registry: run_id -> queue
_run_queues: dict[str, queue.Queue] = {}

# ── Serve frontend ────────────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    index = FRONTEND_DIR / "index.html"
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


# ── API ───────────────────────────────────────────────────────────────────────

class StartRequest(BaseModel):
    model: str = OLLAMA_MODEL
    seed: int = 42
    max_chambers: int = MAX_CHAMBERS


@app.post("/api/start")
def start_run(req: StartRequest):
    run_id = uuid.uuid4().hex[:8]
    q: queue.Queue = queue.Queue()
    _run_queues[run_id] = q

    thread = threading.Thread(
        target=run_agent,
        kwargs={
            "run_id": run_id,
            "model": req.model,
            "seed": req.seed,
            "max_chambers": req.max_chambers,
            "event_queue": q,
        },
        daemon=True,
    )
    thread.start()
    return {"run_id": run_id}


@app.get("/api/stream/{run_id}")
async def stream(run_id: str):
    if run_id not in _run_queues:
        raise HTTPException(status_code=404, detail="Run not found")

    q = _run_queues[run_id]

    async def event_generator() -> AsyncGenerator[dict, None]:
        while True:
            try:
                item = q.get(timeout=30)
            except queue.Empty:
                yield {"event": "ping", "data": ""}
                continue

            yield {
                "event": item["type"],
                "data": json.dumps(item["data"]),
            }

            if item["type"] in ("done", "error"):
                _run_queues.pop(run_id, None)
                break

    return EventSourceResponse(event_generator())


@app.get("/api/log/{run_id}")
def get_log_info(run_id: str):
    """Return the run's log folder path (for manual inspection)."""
    from pathlib import Path
    logs_root = Path(__file__).parent.parent / "logs"
    matches = list(logs_root.glob(f"run_*_{run_id}"))
    if not matches:
        raise HTTPException(status_code=404, detail="Log folder not found yet.")
    return {"log_folder": str(matches[0])}
