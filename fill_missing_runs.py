import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

def fill_missing_runs():
    saved_logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saved_logs')
    
    if not os.path.exists(saved_logs_dir):
        print(f"Directory {saved_logs_dir} doesn't exist.")
        return

    # Regex to capture seed and mode from folder name
    # e.g. run_42_control_20260329_211252_cd68a9f8
    pattern = re.compile(r'^run_(\d+)_([a-zA-Z]+)_')

    existing_runs = set()
    seeds = []
    
    for folder in os.listdir(saved_logs_dir):
        match = pattern.match(folder)
        if match:
            seed = int(match.group(1))
            mode = match.group(2)
            existing_runs.add((seed, mode))
            seeds.append(seed)

    if not seeds:
        print("No existing runs found to determine seed range.")
        return

    min_seed = min(seeds)
    max_seed = max(seeds)
    
    print(f"Detected seed range: {min_seed} to {max_seed}")

    missing_runs = []
    for seed in range(min_seed, max_seed + 1):
        for mode in ['control', 'tool']:
            if (seed, mode) not in existing_runs:
                missing_runs.append((seed, mode))

    if not missing_runs:
        print("All seeds in range have both 'control' and 'tool' runs. Dataset is complete.")
        return

    print(f"Found {len(missing_runs)} missing runs. Starting simulations...")

    # We will invoke the simulate_runs.py script for each missing run
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend', 'simulate_runs.py')
    
    def run_simulation(seed, mode):
        print(f"Starting missing run -> Seed: {seed}, Mode: {mode}")
        cmd = ["python", script_path, "--seed", str(seed), "--mode", mode, "--count", "1"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error running Seed: {seed}, Mode: {mode}")
            print(result.stderr)
        else:
            print(f"Completed missing run -> Seed: {seed}, Mode: {mode}")

    # Use a ThreadPoolExecutor to run them concurrently if desired
    # Limit workers to avoid overloading
    max_workers = 10
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for seed, mode in missing_runs:
            futures.append(executor.submit(run_simulation, seed, mode))
            
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f"A simulation crashed: {e}")

    print("Finished filling all missing runs.")

if __name__ == "__main__":
    fill_missing_runs()
