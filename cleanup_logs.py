import os
import shutil

def cleanup_logs():
    # Base directories to check
    script_dir = os.path.dirname(os.path.abspath(__file__))
    target_folders = ['logs', 'saved_logs']
    
    deleted_count = 0
    
    for folder in target_folders:
        dir_path = os.path.join(script_dir, folder)
        
        if not os.path.exists(dir_path):
            print(f"Directory not found, skipping: {dir_path}")
            continue
            
        print(f"Checking in {dir_path}...")
        
        # Iterate over subdirectories
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            
            # Ensure it's a directory
            if os.path.isdir(item_path):
                full_run_file = os.path.join(item_path, 'full_run.json')
                
                # Delete if full_run.json does not exist
                if not os.path.exists(full_run_file):
                    print(f"Deleting {item_path} (no full_run.json)")
                    try:
                        shutil.rmtree(item_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"Failed to delete {item_path}: {e}")

    print(f"\nCleanup complete. Deleted {deleted_count} incomplete log directories.")

if __name__ == "__main__":
    cleanup_logs()
