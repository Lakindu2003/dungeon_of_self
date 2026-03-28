"""
prompts.py — ALL prompt templates and augmentation functions.

Rules:
- Every raw string lives here.  agent.py imports functions, never raw strings.
- Augment functions are append-only: they take a prompt string and return an
  extended string.  agent.py chains them based on active_skills.
- XML tag contract:
    Strategy decisions:  <action>…</action>  <target>…</target>  <reason>…</reason>
    Answers:             <final_answer>…</final_answer>
    Tool calls:          <tool_call>{"type":"calculator","expr":"…"}</tool_call>
    Memory store:        <memory_store>{"key":"…","value":"…"}</memory_store>
    Reflection:          <reflection>…</reflection>
"""

from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an autonomous agent playing a dungeon game called "Dungeon of Self".

=== GAME RULES ===
- You have HP (health points) and XP (experience points).
- Wrong answers cost you HP. Correct answers give XP.
- XP accumulates toward Skill Point (SP) thresholds. Each threshold crossed awards 1 SP.
- SP can be spent to unlock skills from the skill tree.

=== CALL BUDGET ===
You have a limited number of LLM calls per question:
  - BASE: exactly 1 call to answer.
  - Web Search skill (tool_web): Google Search grounding is active within your answer call (no extra call).
  - Reflection skill: +1 call AFTER your answer call (to review and correct).
  - Calculator: NOT a separate LLM call — it is a synchronous tool evaluated inline.
Do not ask for more information than your budget allows. Use your budget wisely.

=== XML TAGS ===
All your structured output MUST use XML tags so the system can extract it reliably.
For strategy decisions:
  <action>choose_door|flee|reroll|double_down|unlock_skill</action>
  <target>A|B|C|D|skill_id</target>
  <reason>Your reasoning here</reason>

For answers:
  <final_answer>Your answer here</final_answer>
  (optional) <tool_call>{"type":"calculator","expr":"2+2"}</tool_call>
  (optional) <memory_store>{"key":"fact_name","value":"fact_value"}</memory_store>
  (optional) <reflection>Your self-critique here</reflection>

Always enclose reasons, answers, and tool calls within their respective XML tags.
"""

# ─────────────────────────────────────────────────────────────────────────────
# STRATEGY PROMPT
# ─────────────────────────────────────────────────────────────────────────────

def build_strategy_prompt(
    chamber_index: int,
    hp: int,
    xp: int,
    skill_points: int,
    xp_next_threshold: int,
    active_skills: list[str],
    abilities_remaining: dict[str, int],
    doors: list[dict],          # list of {label, categories, level}
    shop_options: list[dict],   # list of {id, name, cost, description}
) -> str:
    doors_text = "\n".join(
        f"  Door {d['label']}: Level {d['level']} | Categories: {', '.join(d['categories'])}"
        for d in doors
    )
    shop_text = (
        "\n".join(
            f"  - {s['id']}: {s['name']} ({s['cost']} SP) — {s['description']}"
            for s in shop_options
        )
        if shop_options
        else "  (none available — either no SP or prerequisites not met)"
    )
    active_text = ", ".join(active_skills) if active_skills else "none"
    abilities_text = "  " + "  ".join(
        f"{k.replace('_',' ').title()}: {v} remaining"
        for k, v in abilities_remaining.items()
    )

    return f"""=== CHAMBER {chamber_index + 1} — CHOOSE YOUR ACTION ===

Your status:  HP={hp}  XP={xp}/{xp_next_threshold} (next SP)  Skill Points={skill_points}
Active skills: {active_text}

Four doors ahead:
{doors_text}

Available ability uses:
{abilities_text}

Skill shop (costs SP):
{shop_text}

You may:
  • Spend a Skill Point to unlock one skill (action=unlock_skill, target=skill_id).
    You can unlock multiple skills — keep responding with unlock_skill until done,
    then choose a door.
  • Enter a door (action=choose_door, target=A/B/C/D).
  • Reroll the four doors (action=reroll) — replaces all 4 with unseen questions.
  • Flee the chamber (action=flee) — you return here later; useful to buy skills first.
  • Declare double-down BEFORE entering (action=double_down, target=A/B/C/D)
    — correct answer gives 2× XP; wrong answer costs 2× HP.

Respond using XML tags:
<action>your_action</action>
<target>your_target_if_applicable</target>
<reason>Your reasoning for this choice</reason>
"""


# ─────────────────────────────────────────────────────────────────────────────
# ANSWER PROMPT (base)
# ─────────────────────────────────────────────────────────────────────────────

def build_answer_prompt(
    question: str,
    level: int,
    active_skills: list[str],
    context_block: str = "",
    memory_block: str = "",
) -> str:
    """
    Assembles the full answer prompt by chaining active augmentations.
    """
    prompt = f"=== QUESTION (GAIA Level {level}) ===\n{question}\n"

    # Inject retrieved context blocks if available
    if memory_block:
        prompt = f"=== YOUR MEMORY ===\n{memory_block}\n\n" + prompt
    if context_block:
        prompt = f"=== RECENT HISTORY ===\n{context_block}\n\n" + prompt

    # Chain prompt augmentations based on active skills
    if "pe_plan" in active_skills:
        prompt = augment_plan(prompt)
    if "pe_cot" in active_skills:
        prompt = augment_cot(prompt)
    if "pe_reflect" in active_skills:
        prompt = augment_reflect_instruction(prompt)

    # Explain tool availability
    tool_lines: list[str] = []
    if "tool_calc" in active_skills:
        tool_lines.append(
            "  Calculator: Wrap a math expression in "
            '<tool_call>{"type":"calculator","expr":"EXPRESSION"}</tool_call>'
        )
    if "tool_memory" in active_skills:
        tool_lines.append(
            "  Memory store: Save a fact with "
            '<memory_store>{"key":"name","value":"content"}</memory_store>'
        )
    if tool_lines:
        prompt += "\n=== AVAILABLE TOOLS ===\n" + "\n".join(tool_lines) + "\n"

    # Call budget reminder
    budget_parts = ["1 (this call)"]
    if "tool_web" in active_skills:
        budget_parts.append("Google Search grounding active within this call (no extra call)")
    if "pe_reflect" in active_skills:
        budget_parts.append("1 upcoming reflection call")
    prompt += f"\nCall budget for this question: {', '.join(budget_parts)}.\n"

    prompt += "\nRespond with:\n<final_answer>Your answer</final_answer>\n"
    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# PROMPT AUGMENTATION FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def augment_cot(prompt: str) -> str:
    """CoT: append a chain-of-thought instruction."""
    return prompt + (
        "\n=== CHAIN OF THOUGHT ===\n"
        "Think through the problem step-by-step before writing your final answer. "
        "Show your reasoning before the <final_answer> tag.\n"
    )


def augment_plan(prompt: str) -> str:
    """Planning: prepend an approach-outline block."""
    header = (
        "=== PLANNING PHASE ===\n"
        "Before answering, briefly outline your approach (1-5 sentences). "
        "This plan will guide your answer.\n\n"
    )
    return header + prompt


def augment_reflect_instruction(prompt: str) -> str:
    """Add a note that a reflection call will follow."""
    return prompt + (
        "\n=== REFLECTION NOTE ===\n"
        "After your initial answer, you will receive a dedicated reflection call "
        "to review and optionally correct it. Focus on giving your best answer now.\n"
    )


# ─────────────────────────────────────────────────────────────────────────────
# REFLECTION PROMPT
# ─────────────────────────────────────────────────────────────────────────────

def build_reflect_prompt(question: str, first_answer: str) -> str:
    return f"""=== REFLECTION CALL ===
Original question: {question}

Your initial answer: {first_answer}

Critically review your answer:
- Is it factually correct?
- Did you make any arithmetic or reasoning errors?
- Is there a better or more precise answer?

Provide your revised answer (or confirm the original if correct).

<reflection>Your critique here</reflection>
<final_answer>Your final (possibly revised) answer</final_answer>
"""


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARISE PROMPT (for Gemini Flash)
# ─────────────────────────────────────────────────────────────────────────────

def build_summarise_prompt(history_text: str) -> str:
    return f"""You are a concise summariser for a dungeon game chat log.
Summarise the following conversation history into a brief paragraph (5-10 sentences).
Preserve key facts, decisions, correct answers, lessons learnt and skill unlocks.

Conversation history:
{history_text}

Write only the summary paragraph, no preamble.
"""
