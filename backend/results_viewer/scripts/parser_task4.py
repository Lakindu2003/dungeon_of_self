import json
import os
import glob

def parse_task4(base_dir):
    data = []
    
    for run_dir in glob.glob(os.path.join(base_dir, "run_*")):
        run_name = os.path.basename(run_dir)
        parts = run_name.split("_")
        if len(parts) >= 3:
            seed = parts[1]
            mode = parts[2]
        else:
            continue
        
        file_path = os.path.join(run_dir, "ability_double_down.json")
        if not os.path.exists(file_path): 
            continue
            
        with open(file_path, "r") as f:
            dd_data = json.load(f)
            
        for ev in dd_data:
            data.append({
                "seed": seed,
                "mode": mode,
                "chamber_index": ev.get("chamber_index"),
                "level": ev.get("level"),
                "category": ev.get("category"),
                "active_skills_count": len(ev.get("active_skills", [])),
                "outcome": ev.get("outcome")
            })

    return data

if __name__ == "__main__":
    base_dir = os.path.join(os.path.dirname(__file__), "../../../saved_logs")
    parsed = parse_task4(base_dir)
    out_path = os.path.join(os.path.dirname(__file__), "parsed_task4.json")
    with open(out_path, "w") as f:
        json.dump(parsed, f, indent=2)
    print(f"Task 4 parsed data written to {out_path}")
