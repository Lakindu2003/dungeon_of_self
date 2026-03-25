/* app.js — Dungeon of Self frontend logic */

// ── State ─────────────────────────────────────────────────────────────────────
let currentRunId = null;
let currentModel = "gemini-3-flash-preview";
let currentState = null;
let eventSource = null;
let chamberHistory = [];   // {index, result: "correct"|"wrong"|"current"|null}[]

const SKILL_IDS = [
  "pe_cot","pe_plan","pe_reflect",
  "ctx_enough","ctx_overload","ctx_summarise",
  "tool_calc","tool_web","tool_memory",
];

const CAT_CLASS = {
  math:        "seg-math",
  science:     "seg-science",
  history:     "seg-history",
  coding:      "seg-coding",
  geography:   "seg-geography",
  reasoning:   "seg-reasoning",
  knowledge:   "seg-knowledge",
};

function catClass(cat) {
  return CAT_CLASS[(cat || "").toLowerCase()] || "seg-default";
}

// ── DOM refs ──────────────────────────────────────────────────────────────────
const startOverlay   = document.getElementById("start-overlay");
const inpModel       = document.getElementById("inp-model");
const inpSeed        = document.getElementById("inp-seed");
const inpMax         = document.getElementById("inp-max");
const btnStart       = document.getElementById("btn-start");

const hpBar          = document.getElementById("hp-bar");
const hpVal          = document.getElementById("hp-val");
const xpBar          = document.getElementById("xp-bar");
const xpVal          = document.getElementById("xp-val");
const spVal          = document.getElementById("sp-val");

const cntReroll      = document.getElementById("cnt-reroll");
const cntFlee        = document.getElementById("cnt-flee");
const cntDouble      = document.getElementById("cnt-double");
const btnReroll      = document.getElementById("btn-reroll");
const btnFlee        = document.getElementById("btn-flee");
const btnDouble      = document.getElementById("btn-double");

const chamberTitle   = document.getElementById("chamber-title");
const chamberSub     = document.getElementById("chamber-subtitle");
const doorsGrid      = document.getElementById("doors-grid");
const dungeonMap     = document.getElementById("dungeon-map");
const agentLog       = document.getElementById("agent-log");

const statCorrect    = document.getElementById("stat-correct");
const statWrong      = document.getElementById("stat-wrong");
const statRooms      = document.getElementById("stat-rooms");
const statSkills     = document.getElementById("stat-skills");

const footerModel    = document.getElementById("footer-model");
const footerRun      = document.getElementById("footer-run");
const footerStatus   = document.getElementById("footer-status");

// End overlay (created dynamically)
let endOverlay = null;

// ── Start ─────────────────────────────────────────────────────────────────────
btnStart.addEventListener("click", async () => {
  const model       = inpModel.value.trim() || "gemini-3-flash-preview";
  const seed        = parseInt(inpSeed.value) || 42;
  const maxChambers = parseInt(inpMax.value) || 20;
  currentModel = model;

  try {
    const res = await fetch("/api/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model, seed, max_chambers: maxChambers }),
    });
    const data = await res.json();
    currentRunId = data.run_id;

    startOverlay.style.display = "none";
    footerModel.textContent = `Model: ${model}`;
    footerRun.textContent   = `Run: ${currentRunId}`;
    footerStatus.textContent = "Status: running";

    initMapGrid(maxChambers);
    connectSSE(currentRunId);
  } catch (err) {
    alert("Failed to start run: " + err.message);
  }
});

// ── SSE ───────────────────────────────────────────────────────────────────────
function connectSSE(runId) {
  eventSource = new EventSource(`/api/stream/${runId}`);

  eventSource.addEventListener("state", (e) => {
    const state = JSON.parse(e.data);
    currentState = state;
    applyState(state);
  });

  eventSource.addEventListener("log", (e) => {
    const entry = JSON.parse(e.data);
    appendLog(entry.role, entry.content, entry.tag);
  });

  eventSource.addEventListener("done", (e) => {
    const state = JSON.parse(e.data);
    applyState(state);
    footerStatus.textContent = "Status: " + (state.status === "dead" ? "dead" : "complete");
    showEndOverlay(state);
    eventSource.close();
  });

  eventSource.addEventListener("error", (e) => {
    const data = JSON.parse(e.data);
    appendLog("ERROR", data.message || "Unknown error", "error");
    footerStatus.textContent = "Status: error";
    eventSource.close();
  });

  eventSource.onerror = () => {
    footerStatus.textContent = "Status: disconnected";
  };
}

// ── Apply state snapshot ──────────────────────────────────────────────────────
function applyState(s) {
  // ── HP bar
  const hpPct = Math.max(0, Math.min(100, (s.hp / 100) * 100));
  hpBar.style.width = hpPct + "%";
  hpVal.textContent = `${s.hp} / 100`;
  if (hpPct < 25) hpBar.style.background = "#ef4444";
  else if (hpPct < 50) hpBar.style.background = "#f97316";
  else hpBar.style.background = "#ef4444";

  // ── XP bar
  const xpNext = s.xp_next_threshold || 1;
  const xpPct  = Math.min(100, (s.xp / xpNext) * 100);
  xpBar.style.width = xpPct + "%";
  xpVal.textContent = `${s.xp} / ${xpNext}`;

  // ── SP
  spVal.textContent = s.skill_points;

  // ── Abilities
  const ab = s.abilities_remaining || {};
  cntReroll.textContent = ab.reroll  ?? 3;
  cntFlee.textContent   = ab.flee    ?? 3;
  cntDouble.textContent = ab.double_down ?? 3;
  btnReroll.classList.toggle("depleted", (ab.reroll  ?? 1) <= 0);
  btnFlee.classList.toggle("depleted",   (ab.flee    ?? 1) <= 0);
  btnDouble.classList.toggle("depleted", (ab.double_down ?? 1) <= 0);

  // ── Skills
  SKILL_IDS.forEach(id => {
    const pill = document.querySelector(`.skill-pill[data-id="${id}"]`);
    if (!pill) return;
    const active = (s.active_skills || []).includes(id);
    pill.classList.toggle("active", active);
  });

  // ── Chamber header
  chamberTitle.textContent = `CHAMBER ${s.chamber_index + 1} — CHOOSE YOUR DOOR`;
  chamberSub.textContent   = "You see four paths ahead. Each door hides a challenge. Choose wisely.";

  // ── Stats
  statCorrect.textContent = s.correct_count;
  statWrong.textContent   = s.wrong_count;
  statRooms.textContent   = s.rooms_visited;
  statSkills.textContent  = s.skills_unlocked_count;

  // ── Map
  updateMap(s.chamber_index, s.total_chambers, s.status);

  // ── Footer status
  if (s.status === "dead") footerStatus.textContent = "Status: dead";
  else if (s.status === "won") footerStatus.textContent = "Status: complete";
  else footerStatus.textContent = "Status: running";
}

// ── Dungeon Map ───────────────────────────────────────────────────────────────
function initMapGrid(totalChambers) {
  dungeonMap.innerHTML = "";
  chamberHistory = [];
  const cols = 5;
  const rows = Math.ceil(totalChambers / cols);
  dungeonMap.style.gridTemplateColumns = `repeat(${cols}, 34px)`;
  for (let i = 0; i < totalChambers; i++) {
    const cell = document.createElement("div");
    cell.className = "map-cell";
    cell.id = `cell-${i}`;
    dungeonMap.appendChild(cell);
    chamberHistory.push({ index: i, result: null });
  }
}

function updateMap(currentIndex, total, status) {
  for (let i = 0; i < total; i++) {
    const cell = document.getElementById(`cell-${i}`);
    if (!cell) continue;
    cell.className = "map-cell";
    if (i < currentIndex) {
      // already visited — try to show result
      const h = chamberHistory[i];
      if (h && h.result === "correct") cell.classList.add("correct");
      else if (h && h.result === "wrong") cell.classList.add("wrong");
      else cell.classList.add("visited");
      cell.textContent = "✓";
    } else if (i === currentIndex) {
      cell.classList.add("current");
      cell.textContent = "•";
    }
  }
}

// Called from log events to update map cell colour
function markChamberResult(index, result) {
  if (chamberHistory[index]) chamberHistory[index].result = result;
  const cell = document.getElementById(`cell-${index}`);
  if (!cell) return;
  cell.className = "map-cell";
  if (result === "correct") { cell.classList.add("correct"); cell.textContent = "✓"; }
  else if (result === "wrong") { cell.classList.add("wrong"); cell.textContent = "✗"; }
}

// ── Door cards ────────────────────────────────────────────────────────────────
// Doors are described in state log events; parse them from log tag "doors"
function renderDoors(doorsData) {
  doorsGrid.innerHTML = "";
  const labels = ["A","B","C","D"];
  doorsData.forEach((d, i) => {
    const card = document.createElement("div");
    card.className = "door-card";
    card.id = `door-card-${i}`;

    const lvlClass = `lv${d.level}`;
    const cats = Array.isArray(d.categories) ? d.categories : [d.category || "?"];

    const tagsHtml = cats.map(c =>
      `<span class="cat-tag">${c} ×1</span>`
    ).join("");

    const segHtml = cats.map(c =>
      `<div class="door-bar-seg ${catClass(c)}"></div>`
    ).join("");

    card.innerHTML = `
      <div class="door-header">
        <div class="door-number">${i + 1}</div>
        <span class="door-level-badge ${lvlClass}">Level ${d.level}</span>
      </div>
      <div class="door-tags">${tagsHtml}</div>
      <div class="door-bar-row">${segHtml}</div>
    `;
    doorsGrid.appendChild(card);
  });
}

// ── Log ───────────────────────────────────────────────────────────────────────
// role: "SYSTEM" | "LLM AGENT" | "RESULT" | "ERROR"
// tag:  "correct" | "wrong" | "unlock" | "reroll" | "flee" | "double_down" | "tool" | "memory" | "reflection" | ...
function appendLog(role, content, tag) {
  const entry = document.createElement("div");
  const roleKey = (role || "").toUpperCase();

  let cls = "system";
  if (roleKey === "LLM AGENT") cls = "llm";
  else if (roleKey === "RESULT" && tag === "correct") cls = "result-c";
  else if (roleKey === "RESULT" && tag === "wrong")   cls = "result-w";

  entry.className = `log-entry ${cls}`;

  // Truncate very long LLM outputs in the log
  let display = content || "";
  if (display.length > 600) display = display.slice(0, 600) + "\n…[truncated]";

  entry.innerHTML = `<div class="log-role">${escapeHtml(role)}</div>${escapeHtml(display)}`;
  agentLog.appendChild(entry);
  agentLog.scrollTop = agentLog.scrollHeight;

  // Side-effects from tags
  if (tag === "correct" && currentState) markChamberResult(currentState.chamber_index, "correct");
  if (tag === "wrong"   && currentState) markChamberResult(currentState.chamber_index, "wrong");
}

// ── End overlay ───────────────────────────────────────────────────────────────
function showEndOverlay(state) {
  if (!endOverlay) {
    endOverlay = document.createElement("div");
    endOverlay.id = "end-overlay";
    endOverlay.innerHTML = `
      <div class="end-card" id="end-card">
        <h2 id="end-title"></h2>
        <p id="end-body"></p>
        <button class="end-btn" onclick="location.reload()">▶ New Run</button>
      </div>`;
    document.body.appendChild(endOverlay);
  }
  const card  = document.getElementById("end-card");
  const title = document.getElementById("end-title");
  const body  = document.getElementById("end-body");
  if (state.status === "dead") {
    card.className = "end-card dead";
    title.textContent = "YOU DIED";
    body.textContent  = `Completed ${state.rooms_visited} chambers. ${state.correct_count} correct, ${state.wrong_count} wrong.`;
  } else {
    card.className = "end-card won";
    title.textContent = "DUNGEON CLEARED";
    body.textContent  = `All ${state.rooms_visited} chambers conquered! ${state.correct_count} correct, ${state.wrong_count} wrong.`;
  }
  endOverlay.classList.add("visible");
}

// ── Utility ───────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Close btn (manual run end) ────────────────────────────────────────────────
document.getElementById("btn-close").addEventListener("click", () => {
  if (eventSource) eventSource.close();
  if (currentState) showEndOverlay({ ...currentState, status: "won" });
});
