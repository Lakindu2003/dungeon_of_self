import json
import os
import re
import glob

def parse_logs(base_dir):
    data = []
    
    for run_dir in glob.glob(os.path.join(base_dir, "run_*")):
        run_name = os.path.basename(run_dir)
        parts = run_name.split("_")
        seed = parts[1]
        mode = parts[2] # "control" or "tool"
        
        full_run_path = os.path.join(run_dir, "full_run.json")
        if not os.path.exists(full_run_path): continue
            
        with open(full_run_path, "r") as f:
            run_data = json.load(f)
            
        final_state = run_data.get("final_state", {})
        
        events = run_data.get("events", [])
        
        questions_attempted = []
        for i, ev in enumerate(events):
            if ev.get("event_type") == "strategy_call":
                # Parse the prompt to find the chosen door
                response = ev.get("response", "")
                
                # Check if it chose a door or doubled down
                action_match = re.search(r'<action>(choose_door|double_down)</action>', response, re.IGNORECASE)
                if not action_match: continue
                
                target_match = re.search(r'<target>([A-D])</target>', response, re.IGNORECASE)
                if not target_match: continue
                
                target = target_match.group(1).upper()
                
                # Extract door details
                prompt = ev.get("prompt", "")
                door_match = re.search(rf'Door {target}: Level (\d+) \| Categories:\s*(.+?)\n', prompt)
                if door_match:
                    level = int(door_match.group(1))
                    categories = door_match.group(2).strip()
                    
                    # Assume correct, override to incorrect later
                    q = {"seed": seed, "mode": mode, "chamber": ev.get("chamber_index"), "action": action_match.group(1).lower(), "door": target, "level": level, "category": categories, "is_correct": True}
                    questions_attempted.append(q)
                    
            elif ev.get("event_type") == "wrong_answer":
                # find the most recent matching question in questions_attempted and set to incorrect
                chamber = ev.get("chamber_index")
                for q in reversed(questions_attempted):
                    if q["chamber"] == chamber:
                        q["is_correct"] = False
                        break
                        
            elif ev.get("event_type") == "ability_double_down":
                chamber = ev.get("chamber_index")
                outcome = ev.get("outcome") # "correct" or "wrong"
                for q in reversed(questions_attempted):
                    if q["chamber"] == chamber:
                        q["is_correct"] = outcome == "correct"
                        break
                        
        data.append({
            "run_name": run_name,
            "seed": seed,
            "mode": mode,
            "final_state": final_state,
            "questions_attempted": questions_attempted
        })
        
    return data

if __name__ == "__main__":
    parsed = parse_logs("/home/lakindu_linux/Desktop/comp3520_prj/dungeon_of_self/saved_logs")
    with open("/home/lakindu_linux/Desktop/comp3520_prj/dungeon_of_self/backend/results_viewer/scripts/parsed_data.json", "w") as f:
        json.dump(parsed, f, indent=2)

