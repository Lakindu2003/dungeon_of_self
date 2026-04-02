import json
import os
import re
import glob

def parse_task2(base_dir):
    data = []
    
    for run_dir in glob.glob(os.path.join(base_dir, "run_*_tool_*")):
        run_name = os.path.basename(run_dir)
        parts = run_name.split("_")
        seed = parts[1]
        
        full_run_path = os.path.join(run_dir, "full_run.json")
        if not os.path.exists(full_run_path): continue
            
        with open(full_run_path, "r") as f:
            run_data = json.load(f)
            
        events = run_data.get("events", [])
        
        # We need to find `unlock_skill` events and correlate them to the subsequent action
        
        current_chamber = -1
        current_doors = []
        
        pending_unlocks = []
        
        for ev in events:
            if ev.get("event_type") == "strategy_call":
                response = ev.get("response", "")
                prompt = ev.get("prompt", "")
                chamber = ev.get("chamber_index")
                
                # Parse doors from prompt
                doors = []
                for match in re.finditer(r'Door ([A-D]): Level (\d+) \| Categories:\s*(.+?)\n', prompt):
                    doors.append({
                        "door": match.group(1),
                        "level": int(match.group(2)),
                        "category": match.group(3).strip()
                    })
                
                action_match = re.search(r'<action>(.+?)</action>', response, re.IGNORECASE)
                if not action_match: continue
                action = action_match.group(1).lower()
                
                target_match = re.search(r'<target>(.+?)</target>', response, re.IGNORECASE)
                target = target_match.group(1) if target_match else None
                
                reason_match = re.search(r'<reason>(.+?)</reason>', response, re.IGNORECASE | re.DOTALL)
                reason = reason_match.group(1).strip() if reason_match else ""
                
                if action == "unlock_skill":
                    pending_unlocks.append({
                        "seed": seed,
                        "chamber": chamber,
                        "skill": target,
                        "reason": reason,
                        "doors": doors
                    })
                else:
                    # An action other than unlock_skill was taken (choose_door, double_down, reroll, flee)
                    # Resolve any pending unlocks
                    for pu in pending_unlocks:
                        action_desc = f"{action} ({target})" if target else action
                        if action in ["choose_door", "double_down"] and target:
                            # Map target to door details
                            chosen_door = next((d for d in doors if d["door"] == target.upper()), None)
                            if chosen_door:
                                action_desc = f"{action} -> Door {target.upper()} ({chosen_door['category']} L{chosen_door['level']})"
                        
                        pu["action_after"] = action_desc
                        data.append(pu)
                    pending_unlocks = []
                    
    return data

if __name__ == "__main__":
    parsed = parse_task2("/home/lakindu_linux/Desktop/comp3520_prj/dungeon_of_self/saved_logs")
    with open("/home/lakindu_linux/Desktop/comp3520_prj/dungeon_of_self/backend/results_viewer/scripts/parsed_task2.json", "w") as f:
        json.dump(parsed, f, indent=2)
