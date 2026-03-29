"""
agent.py — Main autonomous game loop.

Runs on a background thread started by main.py.
Publishes GameState snapshots via a Queue that the SSE endpoint drains.
"""

from __future__ import annotations
import json
import queue
import random
import re
import traceback
import uuid
from collections import defaultdict
from typing import Any

from backend.config import (
    STARTING_HP,
    HP_LOSS_WRONG,
    XP_PER_LEVEL,
    SKILL_POINT_XP_THRESHOLDS,
    CONTEXT_HISTORY_SIZE,
    CONTEXT_SUMMARISE_EVERY,
)
from backend.game.state import GameState
from backend.game.map_builder import (
    Chamber,
    QuestionSlot,
    build_chambers,
    load_questions,
)
from backend.game.skill_tree import (
    SKILL_TREE,
    apply_unlock,
    describe_skill_for_prompt,
    get_available_unlocks,
)
from backend.game.abilities import do_flee, do_reroll, resolve_double_down
from backend.game.scorer import check_answer
from backend.logger.run_logger import RunLogger, extract_tag
from backend.llm import gemini_client
from backend.llm.prompts import (
    SYSTEM_PROMPT,
    build_answer_prompt,
    build_reflect_prompt,
    build_strategy_prompt,
)
from backend.llm.tools.calculator import evaluate as calc_evaluate
from backend.llm.tools.memory import apply_memory_store, format_memory_block


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slot_to_dict(slot: QuestionSlot) -> dict:
    return {
        "task_id": slot.task_id,
        "question": slot.question,
        "category": slot.category,
        "level": slot.level,
    }


def _doors_for_prompt(chamber: Chamber) -> list[dict]:
    labels = ["A", "B", "C", "D"]
    return [
        {
            "label": labels[i],
            "categories": [slot.category],
            "level": slot.level,
        }
        for i, slot in enumerate(chamber.doors)
    ]


def _door_label_to_index(label: str) -> int:
    return {"A": 0, "B": 1, "C": 2, "D": 3}.get(label.upper(), 0)


def _extract_tool_calls(text: str) -> list[dict]:
    """Parse all <tool_call>…</tool_call> JSON blobs from LLM output."""
    calls = []
    for m in re.finditer(r"<tool_call>(.*?)</tool_call>", text, re.DOTALL):
        try:
            calls.append(json.loads(m.group(1).strip()))
        except json.JSONDecodeError:
            pass
    return calls


def _extract_memory_stores(text: str) -> list[dict]:
    """Parse all <memory_store>…</memory_store> JSON blobs from LLM output."""
    stores = []
    for m in re.finditer(r"<memory_store>(.*?)</memory_store>", text, re.DOTALL):
        try:
            stores.append(json.loads(m.group(1).strip()))
        except json.JSONDecodeError:
            pass
    return stores


def _compute_xp_threshold(index: int) -> int:
    """Compute the cumulative XP needed to reach threshold at *index*."""
    return sum(SKILL_POINT_XP_THRESHOLDS[:index + 1])


def _manage_context(state: GameState, new_user_msg: str, new_assistant_msg: str) -> None:
    """Append to chat_history and apply context management based on active skills."""
    state.chat_history.append({"role": "user", "content": new_user_msg})
    state.chat_history.append({"role": "assistant", "content": new_assistant_msg})
    state.summarise_counter += 1

    if "ctx_summarise" in state.active_skills:
        if state.summarise_counter >= CONTEXT_SUMMARISE_EVERY:
            old_msgs = state.chat_history[:-4]  # keep last 2 exchanges
            recent = state.chat_history[-4:]
            history_text = "\n".join(
                f"{m['role'].upper()}: {m['content']}" for m in old_msgs
            )
            summary = gemini_client.summarise(history_text)
            state.chat_history = [
                {"role": "system", "content": f"[History summary]: {summary}"}
            ] + recent
            state.summarise_counter = 0
    elif "ctx_overload" in state.active_skills:
        pass  # full history kept
    elif "ctx_enough" in state.active_skills:
        # Keep only last CONTEXT_HISTORY_SIZE*2 messages (pairs)
        keep = CONTEXT_HISTORY_SIZE * 2
        if len(state.chat_history) > keep:
            state.chat_history = state.chat_history[-keep:]
    else:
        # ctx_base: no history passed
        state.chat_history = []


def _build_context_block(state: GameState) -> str:
    """Format chat_history as a context string for the answer prompt."""
    if not state.chat_history:
        return ""
    return "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in state.chat_history
    )


def _award_xp(state: GameState, amount: int) -> int:
    """Add XP, check thresholds, award SP. Returns number of SP awarded."""
    state.xp += amount
    sp_awarded = 0
    while state.xp_threshold_index < len(SKILL_POINT_XP_THRESHOLDS):
        needed = _compute_xp_threshold(state.xp_threshold_index)
        if state.xp >= needed:
            state.skill_points += 1
            sp_awarded += 1
            state.xp_threshold_index += 1
        else:
            break
    # Update next threshold display value
    if state.xp_threshold_index < len(SKILL_POINT_XP_THRESHOLDS):
        state.xp_next_threshold = _compute_xp_threshold(state.xp_threshold_index)
    else:
        state.xp_next_threshold = 9999  # max skills unlocked
    return sp_awarded


# ── Main agent loop ───────────────────────────────────────────────────────────

def run_agent(
    run_id: str,
    model: str,
    seed: int,
    max_chambers: int,
    event_queue: queue.Queue,
    no_tools_mode: bool = False,
) -> None:
    """
    Entry point for the background thread.
    Pushes dict payloads to event_queue:
      {"type": "state", "data": state.to_dict()}
      {"type": "log",   "data": {"role": ..., "content": ..., "tag": ...}}
      {"type": "done",  "data": state.to_dict()}
      {"type": "error", "data": {"message": ...}}
    """

    def push_state(state: GameState) -> None:
        event_queue.put({"type": "state", "data": state.to_dict()})

    def push_log(role: str, content: str, tag: str = "") -> None:
        event_queue.put({
            "type": "log",
            "data": {"role": role, "content": content, "tag": tag},
        })

    try:
        # ── Initialise ────────────────────────────────────────────────────────
        active_system_prompt = SYSTEM_PROMPT
        if no_tools_mode:
            active_system_prompt += "\n\nNOTE: You are currently running in NO-TOOLS mode. Skill unlocks and tools are DISABLED. Rely solely on your base reasoning capabilities."

        logger = RunLogger(run_id)
        state = GameState(run_id=run_id, run_folder=logger.folder_path)
        state.max_chambers = max_chambers
        state.hp = STARTING_HP
        state.xp_next_threshold = SKILL_POINT_XP_THRESHOLDS[0]

        questions = load_questions()
        chambers = build_chambers(questions, seed=seed)
        # Limit to max_chambers
        chambers = chambers[:max_chambers]
        state.total_chambers = len(chambers)
        remaining_pool: list[QuestionSlot] = []  # questions not yet in any chamber
        rng = random.Random(seed)

        # Collect overflow questions into remaining_pool
        all_ids_in_chambers = {s.task_id for c in chambers for s in c.doors}
        remaining_pool = [q for q in questions if q.task_id not in all_ids_in_chambers]

        category_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "wrong": 0})
        answered_ids_set: set[str] = set()

        push_log("SYSTEM", f"Dungeon of Self initialised. {len(chambers)} chambers loaded. Run ID: {run_id}")
        push_state(state)

        # ── Chamber loop ──────────────────────────────────────────────────────
        chamber_iter = 0
        while chamber_iter < len(chambers) and state.hp > 0:
            chamber = chambers[chamber_iter]
            state.chamber_index = chamber_iter
            state.rooms_visited += 1
            push_log("SYSTEM", f"You enter Chamber {chamber_iter + 1}. Four doors are available.")
            push_state(state)

            # ── Strategy loop (unlock / reroll / flee / choose door) ──────────
            door_chosen: int | None = None
            double_down_flagged = False
            strategy_raw = ""

            while door_chosen is None:
                available_skills = [] if no_tools_mode else get_available_unlocks(state.active_skills, state.skill_points)
                shop_opts = [
                    {
                        "id": s.id,
                        "name": s.name,
                        "cost": s.cost,
                        "description": s.description,
                    }
                    for s in available_skills
                ]
                doors_info = _doors_for_prompt(chamber)
                strategy_prompt = build_strategy_prompt(
                    chamber_index=chamber_iter,
                    hp=state.hp,
                    xp=state.xp,
                    skill_points=state.skill_points,
                    xp_next_threshold=state.xp_next_threshold,
                    active_skills=state.active_skills,
                    abilities_remaining=state.abilities_remaining,
                    doors=doors_info,
                    shop_options=shop_opts,
                )

                push_log("SYSTEM", f"Prompting LLM for strategy (Chamber {chamber_iter + 1})")
                strategy_raw = gemini_client.call(
                    messages=[{"role": "user", "content": strategy_prompt}],
                    system=active_system_prompt,
                )
                push_log("LLM AGENT", strategy_raw)
                logger.log_event("strategy_call", {
                    "chamber_index": chamber_iter,
                    "prompt": strategy_prompt,
                    "response": strategy_raw,
                })

                action = extract_tag(strategy_raw, "action").lower()
                target = extract_tag(strategy_raw, "target").upper()

                # ── unlock_skill ──────────────────────────────────────────────
                if action == "unlock_skill":
                    if no_tools_mode:
                        push_log("SYSTEM", "Skill unlock error: Skills and tools are disabled in this mode.")
                        continue
                    
                    skill_id = target.lower()
                    new_skills, new_sp, err = apply_unlock(
                        skill_id, state.active_skills, state.skill_points
                    )
                    if err:
                        push_log("SYSTEM", f"Skill unlock error: {err}")
                    else:
                        state.active_skills = new_skills
                        state.skill_points = new_sp
                        state.skills_unlocked_count += 1
                        sname = SKILL_TREE[skill_id].name
                        push_log("SYSTEM", f"Skill unlocked: {sname}", tag="unlock")
                        logger.log_skill_unlock(
                            skill_id=skill_id,
                            skill_name=sname,
                            sp_cost=SKILL_TREE[skill_id].cost,
                            xp_at_time=state.xp,
                            hp_at_time=state.hp,
                            chamber_index=chamber_iter,
                            llm_raw_response=strategy_raw,
                            chat_history_snippet=list(state.chat_history),
                        )
                    push_state(state)
                    continue   # re-prompt strategy

                # ── reroll ────────────────────────────────────────────────────
                elif action == "reroll":
                    doors_before = [_slot_to_dict(s) for s in chamber.doors]
                    chamber, remaining_pool, new_ab, err = do_reroll(
                        chamber, remaining_pool, answered_ids_set, state.abilities_remaining, rng
                    )
                    if err:
                        push_log("SYSTEM", f"Reroll error: {err}")
                    else:
                        state.abilities_remaining = new_ab
                        doors_after = [_slot_to_dict(s) for s in chamber.doors]
                        push_log("SYSTEM", "Chamber doors rerolled.", tag="reroll")
                        logger.log_reroll(
                            chamber_index=chamber_iter,
                            doors_before=doors_before,
                            doors_after=doors_after,
                            active_skills=list(state.active_skills),
                            llm_raw_response=strategy_raw,
                        )
                    push_state(state)
                    continue

                # ── flee ──────────────────────────────────────────────────────
                elif action == "flee":
                    new_ab, err = do_flee(state.abilities_remaining)
                    if err:
                        push_log("SYSTEM", f"Flee error: {err}")
                    else:
                        state.abilities_remaining = new_ab
                        push_log("SYSTEM", "Fled the chamber. Returning to same chamber.", tag="flee")
                        logger.log_flee(
                            chamber_index=chamber_iter,
                            doors_available=[_slot_to_dict(s) for s in chamber.doors],
                            active_skills=list(state.active_skills),
                            chat_at_point=list(state.chat_history),
                            llm_raw_response=strategy_raw,
                        )
                    push_state(state)
                    continue

                # ── double_down ───────────────────────────────────────────────
                elif action == "double_down":
                    if state.abilities_remaining["double_down"] <= 0:
                        push_log("SYSTEM", "No Double-downs remaining.")
                        push_state(state)
                        continue
                    door_chosen = _door_label_to_index(target)
                    double_down_flagged = True
                    push_log("SYSTEM", f"Double-down declared on Door {target}.", tag="double_down")

                # ── choose_door ───────────────────────────────────────────────
                elif action == "choose_door":
                    door_chosen = _door_label_to_index(target)
                    push_log("SYSTEM", f"Door {target} chosen.")

                else:
                    # Fallback: default to door A
                    push_log("SYSTEM", f"Unrecognised action '{action}'. Defaulting to Door A.")
                    door_chosen = 0

            # ── Answer phase ──────────────────────────────────────────────────
            slot = chamber.doors[door_chosen]
            answered_ids_set.add(slot.task_id)
            push_log("SYSTEM", f"Entering door — Question (Level {slot.level}, {slot.category}): {slot.question}")

            # Pre-answer: web search — Gemini native grounding (no extra call)
            use_web_search = "tool_web" in state.active_skills

            # Memory block
            memory_block = format_memory_block(state.memory_store) if "tool_memory" in state.active_skills else ""

            # Context block
            context_block = _build_context_block(state)

            # Build and send answer prompt
            answer_prompt = build_answer_prompt(
                question=slot.question,
                level=slot.level,
                active_skills=state.active_skills,
                context_block=context_block,
                memory_block=memory_block,
            )
            push_log("SYSTEM", f"Prompting LLM for answer (1 call budget)")
            answer_raw = gemini_client.call(
                messages=[{"role": "user", "content": answer_prompt}],
                system=active_system_prompt,
                use_web_search=use_web_search,
            )
            push_log("LLM AGENT", answer_raw)

            # Handle calculator tool calls
            tool_calls = _extract_tool_calls(answer_raw)
            calc_results: list[str] = []
            for tc in tool_calls:
                if tc.get("type") == "calculator":
                    result = calc_evaluate(tc.get("expr", ""))
                    calc_results.append(f"calc({tc.get('expr')}) = {result}")
                    push_log("SYSTEM", f"Calculator: {tc.get('expr')} = {result}", tag="tool")

            # Handle memory stores
            mem_stores = _extract_memory_stores(answer_raw)
            for ms in mem_stores:
                k, v = ms.get("key", ""), ms.get("value", "")
                if k:
                    state.memory_store = apply_memory_store(state.memory_store, k, v)
                    push_log("SYSTEM", f"Memory stored: {k} = {v}", tag="memory")

            # Extract first answer
            first_answer = extract_tag(answer_raw, "final_answer")

            # Reflection call (if unlocked)
            reflect_raw = ""
            if "pe_reflect" in state.active_skills and first_answer:
                reflect_prompt = build_reflect_prompt(slot.question, first_answer)
                push_log("SYSTEM", "Reflection call invoked.")
                reflect_raw = gemini_client.call(
                    messages=[{"role": "user", "content": reflect_prompt}],
                    system=active_system_prompt,
                )
                push_log("LLM AGENT", reflect_raw, tag="reflection")
                revised = extract_tag(reflect_raw, "final_answer")
                if revised:
                    first_answer = revised

            llm_answer = first_answer or answer_raw.strip()

            # ── Score ─────────────────────────────────────────────────────────
            is_correct, norm_llm, norm_expected = check_answer(llm_answer, slot.final_answer)

            # Apply double-down multiplier
            if double_down_flagged:
                new_hp, new_xp, new_ab, hp_delta, xp_delta, _ = resolve_double_down(
                    is_correct=is_correct,
                    level=slot.level,
                    hp=state.hp,
                    xp=state.xp,
                    abilities_remaining=state.abilities_remaining,
                )
                state.hp = new_hp
                state.xp = new_xp
                state.abilities_remaining = new_ab

                logger.log_double_down(
                    chamber_index=chamber_iter,
                    task_id=slot.task_id,
                    question=slot.question,
                    level=slot.level,
                    category=slot.category,
                    active_skills=list(state.active_skills),
                    outcome="correct" if is_correct else "wrong",
                    hp_delta=hp_delta,
                    xp_delta=xp_delta,
                    chat_for_question=[
                        {"role": "user", "content": answer_prompt},
                        {"role": "assistant", "content": answer_raw},
                    ],
                    llm_raw_response=strategy_raw,
                )
                state.double_down_active = False

                if is_correct and xp_delta > 0:
                    _award_xp(state, 0)  # recalculate threshold display (xp already added)
                    state.correct_count += 1
                    result_msg = f"✓ Correct! (Double-down) +{xp_delta} XP"
                    push_log("RESULT", result_msg, tag="correct")
                else:
                    state.wrong_count += 1
                    result_msg = f"✗ Wrong! (Double-down) {hp_delta} HP. Correct: {slot.final_answer}"
                    push_log("RESULT", result_msg, tag="wrong")

            elif is_correct:
                xp_gain = XP_PER_LEVEL.get(slot.level, 1)
                sp_awarded = _award_xp(state, xp_gain)
                state.correct_count += 1
                result_msg = f"✓ Correct! +{xp_gain} XP"
                if sp_awarded:
                    result_msg += f" — {sp_awarded} Skill Point(s) awarded!"
                push_log("RESULT", result_msg, tag="correct")
            else:
                state.hp = max(0, state.hp - HP_LOSS_WRONG)
                state.wrong_count += 1
                result_msg = f"✗ Wrong! -{HP_LOSS_WRONG} HP. Correct answer: {slot.final_answer}"
                push_log("RESULT", result_msg, tag="wrong")

                logger.log_wrong_answer(
                    task_id=slot.task_id,
                    question=slot.question,
                    category=slot.category,
                    level=slot.level,
                    llm_answer=llm_answer,
                    correct_answer=slot.final_answer,
                    active_skills=list(state.active_skills),
                    chamber_index=chamber_iter,
                    chat_log_for_question=[
                        {"role": "user", "content": answer_prompt},
                        {"role": "assistant", "content": answer_raw},
                    ],
                    llm_raw_response=answer_raw,
                )

            # Update category stats
            category_stats[slot.category]["correct" if is_correct else "wrong"] += 1
            logger.update_category_accuracy(
                {
                    cat: {
                        **v,
                        "accuracy": round(
                            v["correct"] / max(1, v["correct"] + v["wrong"]) * 100, 1
                        ),
                    }
                    for cat, v in category_stats.items()
                }
            )

            # Check XP threshold notification
            if state.xp_threshold_index < len(SKILL_POINT_XP_THRESHOLDS):
                remaining_to_next = state.xp_next_threshold - state.xp
                push_log("SYSTEM", f"XP threshold: next SP at {state.xp_next_threshold} XP (need {remaining_to_next} more).")

            # Update context history
            _manage_context(state, answer_prompt, answer_raw)

            push_state(state)

            # ── Check game-over ───────────────────────────────────────────────
            if state.hp <= 0:
                logger.log_memory_store(chamber_iter, state.memory_store)
                state.status = "dead"
                push_log("SYSTEM", "HP reached 0. Game over.")
                push_state(state)
                break

            logger.log_memory_store(chamber_iter, state.memory_store)
            chamber_iter += 1

        # ── Run complete ──────────────────────────────────────────────────────
        if state.status != "dead":
            state.status = "won"
            push_log("SYSTEM", "All chambers cleared. Run complete!")
            push_state(state)

        category_stats_final = {
            cat: {
                **v,
                "accuracy": round(v["correct"] / max(1, v["correct"] + v["wrong"]) * 100, 1),
            }
            for cat, v in category_stats.items()
        }
        logger.finalise(state.to_dict(), category_stats_final)
        push_log("SYSTEM", f"Logs saved to: {logger.folder_path}")

        event_queue.put({"type": "done", "data": state.to_dict()})

    except Exception:
        tb = traceback.format_exc()
        event_queue.put({"type": "error", "data": {"message": tb}})
