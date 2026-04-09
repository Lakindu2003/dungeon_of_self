import json
import os
import glob

def parse_memory(base_dir):
    data = []
    
    for run_dir in glob.glob(os.path.join(base_dir, "run_*")):
        run_name = os.path.basename(run_dir)
        parts = run_name.split("_")
        if len(parts) >= 3:
            seed = parts[1]
            mode = parts[2]
        else:
            continue
        
        file_path = os.path.join(run_dir, "memory.json")
        if not os.path.exists(file_path): 
            continue
            
        try:
            with open(file_path, "r") as f:
                memory_data = json.load(f)
                
            for ev in memory_data:
                # Calculate number of items stored in memory for this chamber
                mem_store = ev.get("memory_store", {})
                num_items = len(mem_store.keys())
                
                data.append({
                    "run_name": run_name,
                    "seed": seed,
                    "mode": mode,
                    "chamber_index": ev.get("chamber_index"),
                    "memory_items_count": num_items,
                    "memory_store": mem_store
                })
        except json.JSONDecodeError:
            pass

    return data

if __name__ == "__main__":
    base_dir = os.path.join(os.path.dirname(__file__), "../../../saved_logs")
    parsed = parse_memory(base_dir)
    out_path = os.path.join(os.path.dirname(__file__), "parsed_memory.json")
    with open(out_path, "w") as f:
        json.dump(parsed, f, indent=2)
    print(f"Memory parsed data written to {out_path} ({len(parsed)} memory items extracted)")
