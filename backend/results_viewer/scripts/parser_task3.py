import json
import os
import re
import glob

def parse_task3(base_dir):
    data = []
    
    for run_dir in glob.glob(os.path.join(base_dir, "run_*")):
        run_name = os.path.basename(run_dir)
        parts = run_name.split("_")
        if len(parts) >= 3:
            seed = parts[1]
            mode = parts[2]
        else:
            continue
        
        full_run_path = os.path.join(run_dir, "full_run.json")
        if not os.path.exists(full_run_path): continue
            
        with open(full_run_path, "r") as f:
            run_data = json.load(f)
            
        events = run_data.get("events", [])
        
        last_mistake_chamber = -1
        mistake_details = None
        
        for ev in events:
            if ev.get("event_type") == "wrong_answer":
                last_mistake_chamber = ev.get("chamber_index")
                mistake_details = {
                    "category": ev.get("category"),
                    "level": ev.get("level")
                }
            
            elif ev.get("event_type") == "strategy_call":
                current_chamber = ev.get("chamber_index", -1)
                
                if mistake_details and current_chamber == last_mistake_chamber + 1:
                    prompt = ev.get("prompt", "")
                    response = ev.get("response", "")
                    
                    # Parse doors from prompt
                    doors = []
                    for match in re.finditer(r'Door ([A-D]): Level (\d+) \| Categories:\s*(.+?)\n', prompt):
                        doors.append({
                            "door": match.group(1),
                            "level": int(match.group(2)),
                            "category": match.group(3).strip()
                        })
                    
                    action_match = re.search(r'<action>(.+?)</action>', response, re.IGNORECASE)
                    action = action_match.group(1).lower() if action_match else "unknown"
                    
                    target_match = re.search(r'<target>(.+?)</target>', response, re.IGNORECASE)
                    target = target_match.group(1) if target_match else None
                    
                    reason_match = re.search(r'<reason>(.+?)</reason>', response, re.IGNORECASE | re.DOTALL)
                    reason = reason_match.group(1).strip() if reason_match else ""
                    
                    # If this is unlock_skill, we might loop. But for simplicity, we just log every action they took right after a mistake, or only the final door choice?
                    # The prompt says: "The actual chamber/question the LLM chose to enter next. The LLM's exact stated reasoning for choosing that specific chamber."
                    # If action is unlock_skill, they haven't chosen a chamber yet. We should wait until they choose a door/reroll/double_down.
                    if action == "unlock_skill":
                        continue
                        
                    action_desc = f"{action} ({target})" if target else action
                    if action in ["choose_door", "double_down"] and target:
                        chosen_door = next((d for d in doors if d["door"] == target.upper()), None)
                        if chosen_door:
                            action_desc = f"{action.replace('_', ' ').title()} -> {chosen_door['category']} (L{chosen_door['level']})"
                            
                    data.append({
                        "seed": seed,
                        "mode": mode,
                        "chamber_after_mistake": current_chamber + 1, # 1-indexed turn
                        "mistake_category": mistake_details["category"],
                        "mistake_level": mistake_details["level"],
                        "doors_available": doors,
                        "action_taken": action_desc,
                        "reason": reason
                    })
                    
                    # Prevent logging again for the same chamber if there are multiple strategy calls
                    mistake_details = None

    return data

if __name__ == "__main__":
    base_dir = os.path.join(os.path.dirname(__file__), "../../../saved_logs")
    parsed = parse_task3(base_dir)
    out_path = os.path.join(os.path.dirname(__file__), "parsed_task3.json")
    with open(out_path, "w") as f:
        json.dump(parsed, f, indent=2)
    print(f"Task 3 parsed data written to {out_path}")
