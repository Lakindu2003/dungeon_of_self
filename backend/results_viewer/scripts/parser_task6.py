import json
import os
import glob

def parse_task6(base_dir):
    data = []

    for run_dir in glob.glob(os.path.join(base_dir, "run_*")):
        run_name = os.path.basename(run_dir)
        
        if "control" in run_dir:
            mode = "control"
        elif "tool" in run_dir:
            mode = "tool"
        else:
            continue
            
        file_path = os.path.join(run_dir, "ability_reroll.json")
        if not os.path.exists(file_path): 
            continue

        with open(file_path, "r") as f:
            text = f.read().strip()
            if not text: continue
            try:
                f_data = json.loads(text)
            except json.JSONDecodeError:
                continue
            
        for ev in f_data:
            doors = ev.get("doors_available", [])
            avg_lvl = sum(d["level"] for d in doors) / max(1, len(doors))
            
            data.append({
                "run": run_name,
                "mode": mode,
                "chamber_index": ev.get("chamber_index"),
                "avg_door_level": avg_lvl,
                "active_skills_count": len(ev.get("active_skills", [])),
                "reason": ev.get("reason")
            })

    return data

if __name__ == "__main__":
    base_dir = os.path.join(os.path.dirname(__file__), "../../../saved_logs")
    parsed = parse_task6(base_dir)
    out_path = os.path.join(os.path.dirname(__file__), "parsed_task6.json")

    with open(out_path, "w") as f:
        json.dump(parsed, f, indent=2)
    print(f"Task 6 parsed data written to {out_path} ({len(parsed)} rerolls)")
