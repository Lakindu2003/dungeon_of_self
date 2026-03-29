# Dungeon of Self

**Are LLMs self-aware?**

An autonomous dungeon-crawler where an LLM agent navigates a series of GAIA-benchmark question chambers. The agent can unlock skills (chain-of-thought, web search, memory, etc.) using earned XP — if it is self-aware, it should recognise its own weaknesses and choose skills accordingly.

---

## Setup

```bash
# 1. Clone and enter the repo
git clone https://github.com/Lakindu2003/dungeon_of_self.git
cd dungeon_of_self

# 2. Create conda environment and install dependencies
conda create -n dungeon_of_self python=3.12 -y
conda activate dungeon_of_self
pip install -r requirements.txt

# 3. Configure API keys
cp .env.example .env
# Edit .env and fill in:
#   GEMINI_API_KEY     — Google Gemini Flash key (used for all LLM calls and search grounding)
#   GEMINI_MODEL       — (default: gemini-3-flash-preview)
#   MAX_CHAMBERS       — maximum rooms per run (default: 20)

# 4. Download and process dataset
# Run the "Downloading and processing dataset" code block in the data_hander.ipynb jupyter notebook.
```

## Run

```bash
# Make sure your conda env is active, then:
conda activate dungeon_of_self
python backend/main.py

# To run base Gemini with no skills/tools:
python backend/main.py --no-tools
```

This will automatically open `http://localhost:8000` in your browser. Enter your seed and max chambers, then click **Start Run**. The LLM plays fully autonomously.

---

## Project Structure

```
backend/
  config.py              — all tunable constants (HP, XP, skill costs, etc.)
  main.py                — FastAPI app (SSE stream + static serving)
  data/gaia_dummy.csv    — dummy GAIA dataset (replace with real data)
  game/
    state.py             — GameState dataclass
    map_builder.py       — load CSV, build chambers, reroll logic
    skill_tree.py        — skill registry with prerequisites and costs
    scorer.py            — normalised answer comparison
    abilities.py         — Reroll / Flee / Double-down
  llm/
    agent.py             — autonomous game loop (runs on background thread)
    prompts.py           — ALL prompt templates and augmentation functions
    gemini_client.py     — Gemini 3.0 Flash client (handles all LLM calls + native web search)
    tools/
      calculator.py      — sandboxed Python expression evaluator
      memory.py          — key-value memory helpers
  logger/
    run_logger.py        — writes per-run log folder
frontend/
  index.html / style.css / app.js   — dark UI, live SSE updates
logs/                    — auto-created; one folder per run
```

## Skill Tree

| Category           | Skills (sequential)                         |
| ------------------ | ------------------------------------------- |
| Prompt Engineering | Base → CoT → Plan+Reflect → Reflection++ |
| Context            | Base → Enough → Overload → Summariser    |
| Tools (parallel)   | Calc, Web Search, Memory                    |

## Logs (per run)

Each run writes to `logs/run_{timestamp}_{id}/`:

| File                         | Contents                                |
| ---------------------------- | --------------------------------------- |
| `full_run.json`            | Complete event log                      |
| `skill_unlocks.json`       | Unlock order + LLM reasons              |
| `skills_summary.json`      | Flat list of unlocked skills            |
| `incorrect_answers.json`   | Wrong answers with active tools + chat  |
| `category_accuracy.json`   | Per-category accuracy breakdown         |
| `ability_reroll.json`      | Doors before/after each reroll + reason |
| `ability_flee.json`        | Context and reason for each flee        |
| `ability_double_down.json` | Outcome, HP/XP delta, reason per use    |

## Using Real GAIA Data

Replace `backend/data/gaia_dummy.csv` with the real GAIA validation set. Required columns:

```
task_id, Question, Level, Final answer, file_name, file_path, Annotator Metadata, category
```

Add a `category` column manually (the original dataset does not include one). Rows with a non-empty `file_name` are automatically skipped.
