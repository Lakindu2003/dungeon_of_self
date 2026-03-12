# GAIA Annotator UI

A standalone web tool for manually annotating GAIA benchmark questions with category labels. This annotator was built to produce a `task_id → category` mapping file that feeds into the **Dungeon of Self** game engine, which uses categories to route questions to the appropriate dungeon doors.

---

## Purpose

The GAIA validation dataset (`gaia_validation.csv`) does not include category labels. Before running the dungeon game, each question needs to be assigned a category (e.g. Math, Science, Reasoning) so the map builder can construct thematically consistent chambers. This tool provides a fast, keyboard-friendly interface for that annotation task.

---

## File Structure

```
backend/data_annotator/
├── app.py              # FastAPI server (port 5000)
├── index.html          # Single-page annotation UI
├── categories.json     # Editable list of valid category labels
├── annotations.csv     # Output file — created automatically on first save
└── annotatorUI.md      # This file
```

**Input:** `backend/data/gaia_validation.csv`  
**Output:** `backend/data_annotator/annotations.csv` — two columns: `task_id`, `category`

---

## How to Run

### Prerequisites

The conda environment `dungeon_of_self` must be set up (see the project README). The annotator reuses the same environment — no extra packages needed.

```bash
conda activate dungeon_of_self
```

### Start the server

From the project root (`dungeon_of_self/`):

```bash
python3 backend/data_annotator/app.py
```

The browser opens automatically at `http://localhost:5000`. If it does not, open it manually.

---

## Using the UI

![annotator ui flow](https://i.imgur.com/placeholder.png)

1. **Progress bar** at the top shows how many of the 127 questions have been annotated.
2. Each question is shown **one at a time** with its GAIA difficulty level (1–3) and task ID.
3. **Select a category** from the dropdown — the annotation saves instantly (no Save button needed) and the UI jumps to the next unannotated question automatically.
4. Use the **Prev / Next** buttons or **← →** arrow keys to revisit any question.
5. Use **"Next unannotated ↓"** to skip ahead to the next question that hasn't been labelled yet.
6. Re-selecting a category on an already-annotated question **overwrites** the previous label.

---

## Modifying Categories

To add, remove, or rename categories, edit `categories.json`:

```json
{
  "categories": [
    "Math",
    "Science",
    "History",
    "Coding",
    "Geography",
    "Reasoning",
    "Knowledge",
    "Language",
    "Other"
  ]
}
```

Save the file and **refresh the browser** — the dropdown updates immediately. No server restart needed.

---

## Output Format

`annotations.csv` is a plain CSV with two columns:

```
task_id,category
c61d22de-5f6c-4958-a7f6-5e9707bd3466,Reasoning
17b5a6a3-bc87-42e8-b0fb-6ab0781ef2cc,Science
...
```

Each row represents one annotated question. The file is created on the first annotation and updated incrementally — no data is lost if the server is restarted mid-session.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serves the annotation UI (`index.html`) |
| `GET` | `/api/questions` | Returns all 127 questions as JSON |
| `GET` | `/api/annotations` | Returns current annotations as `{task_id: category}` |
| `GET` | `/api/categories` | Returns the category list from `categories.json` |
| `POST` | `/api/annotate` | Body: `{"task_id": "…", "category": "…"}` — saves/overwrites one annotation |
