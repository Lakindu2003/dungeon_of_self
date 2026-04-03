import os
import glob
import subprocess
import sys

def clean_up_old_files(pattern="parsed*.json"):
    """Finds and deletes all files matching the given pattern."""
    files_to_delete = glob.glob(pattern)
    
    if not files_to_delete:
        print(f"No files matching '{pattern}' found to delete.")
        return

    print(f"--- Deleting old data files ({pattern}) ---")
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            print(f"🗑️ Deleted: {file_path}")
        except Exception as e:
            print(f"⚠️ Could not delete {file_path}: {e}")
    print("-" * 40)

def run_parser_scripts(pattern="parser*.py"):
    """Finds and runs all python scripts matching the pattern."""
    # Get all matching scripts and sort them so they run in order (parser.py, then parser_task2.py, etc.)
    scripts = sorted(glob.glob(pattern))
    
    # Prevent the script from accidentally trying to run itself if you named it something like 'parser_runner.py'
    current_script_name = os.path.basename(__file__)
    if current_script_name in scripts:
        scripts.remove(current_script_name)

    if not scripts:
        print(f"No scripts matching '{pattern}' found.")
        return

    print(f"--- Running scripts ({pattern}) ---")
    for script in scripts:
        print(f"\n🚀 Starting {script}...")
        try:
            # sys.executable ensures it uses the same Python environment you are currently in
            subprocess.run([sys.executable, script], check=True)
            print(f"✅ Successfully finished {script}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error: {script} crashed with exit code {e.returncode}.")
            print("Stopping execution of remaining scripts.")
            break

if __name__ == "__main__":
    try:
        # Change to the directory where the parser scripts are located
        os.chdir('backend/results_viewer/scripts')
    except Exception as e:
        print(f"Error occurred while changing directory: {e}")
        print(f"Current directory: {os.getcwd()}")

    # 1. Delete all JSON files starting with "parsed"    
    clean_up_old_files("parsed*.json")
    
    # 2. Run all Python files starting with "parser"
    run_parser_scripts("parser*.py")
    
    print("\n🎉 All tasks complete!")