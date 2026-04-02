import argparse
import queue
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure imports work when running `python backend/simulate_runs.py`
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.llm.agent import run_agent
from backend.config import GEMINI_MODEL

def simulate_single_run(seed, no_tools_mode, chambers, mode_name, worker_id):
    run_id = uuid.uuid4().hex[:8]
    q = queue.Queue()

    print(f"[Worker {worker_id}] --- Starting run [{mode_name.upper()} mode, Seed: {seed}, Max Chambers: {chambers}] ---")

    thread = threading.Thread(
        target=run_agent,
        kwargs={
            "run_id": run_id,
            "model": GEMINI_MODEL,
            "seed": seed,
            "max_chambers": chambers,
            "event_queue": q,
            "no_tools_mode": no_tools_mode,
        },
        daemon=True,
    )
    thread.start()

    # Print partial updates as the agent runs
    while True:
        try:
            event = q.get(timeout=1.0)
            ev_type = event.get("type")
            if ev_type in ("done", "error"):
                print(f"[Worker {worker_id}] Run [Seed: {seed}] ended with status: {ev_type}")
                break
            elif ev_type == "state_update":
                # We won't use carriage return \r to avoid text overlapping from multiple multiple workers
                state = event.get("data", {})
                hp = state.get("hp", "?")
                idx = state.get("chamber_index", "?")
                # Optional: you can uncomment the next line for heavy verbose logging, but better to keep quiet when concurrent.
                # print(f"[Worker {worker_id}] [Seed: {seed}] Chamber: {idx} | HP: {hp}")
                pass
        except queue.Empty:
            pass
        
        if not thread.is_alive():
            print(f"[Worker {worker_id}] Run [Seed: {seed}] Thread unexpectedly died!")
            break

def main():
    parser = argparse.ArgumentParser(description="Headless simulation of Dungeon of Self runs.")
    parser.add_argument("--seed", type=int, default=42, help="Starting seed for runs")
    parser.add_argument("--mode", type=str, choices=["tool", "control"], required=True, help="Mode to run the game in")
    parser.add_argument("--count", type=int, default=1, help="Number of games to simulate")
    parser.add_argument("--chambers", type=int, default=10, help="Number of chambers per run")
    parser.add_argument("--workers", type=int, default=1, help="Number of simultaneous workers")
    args = parser.parse_args()

    no_tools_mode = (args.mode == "control")

    print(f"\n--- Launching {args.count} simulations with {args.workers} concurrent workers ---")

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = []
        for i in range(args.count):
            current_seed = args.seed + i
            # Submit to ThreadPoolExecutor
            futures.append(
                executor.submit(simulate_single_run, current_seed, no_tools_mode, args.chambers, args.mode, i+1)
            )

        # Wait for all runs to finish
        for future in as_completed(futures):
            # If the run throws an exception, it will surface here
            try:
                future.result()
            except Exception as e:
                print(f"A simulation thread crashed: {e}")

    print("\n--- All simulations completed ---")

if __name__ == "__main__":
    main()
