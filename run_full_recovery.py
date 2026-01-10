import subprocess
import sys
import os
import logging
from typing import List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_script(script_name: str) -> bool:
    """Run a python script and return True if successful"""
    logging.info(f"--- Starting: {script_name} ---")
    try:
        # Check if file exists first
        if not os.path.exists(script_name):
            logging.error(f"Script not found: {script_name}")
            return False

        # Run script
        
        # Determine python executable: prefer .venv if exists
        python_exe = sys.executable
        venv_python = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
        if os.path.exists(venv_python):
            python_exe = venv_python
            logging.info(f"Using venv python: {python_exe}")
        
        result = subprocess.run([python_exe, script_name], check=True)
        logging.info(f"--- Finished: {script_name} (Exit Code: {result.returncode}) ---\n")
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logging.error(f"--- Failed: {script_name} (Exit Code: {e.returncode}) ---")
        return False
    except Exception as e:
        logging.error(f"Error running {script_name}: {e}")
        return False

def main():
    print("==============================================")
    print("      Notion Image Full Recovery Pipeline     ")
    print("==============================================")
    print("1. Permanent-ize Images (Notion Upload via Proxy)")
    print("2. Export to Google Drive (DOCX)")
    print("==============================================\n")

    import os
    
    # Step 1: Fix Images (Upload to Notion)
    # This now uses Proxy Method if needed to rescue expired images
    if not run_script("notion_image_fixer.py"):
        print("Stopping due to error in notion_image_fixer.py")
        sys.exit(1)

    # Step 2: Sync to Drive
    if not run_script("notion_to_drive_sync.py"):
         print("Stopping due to error in notion_to_drive_sync.py")
         sys.exit(1)

    print("\n✅ Full Recovery Pipeline Completed Successfully!")

if __name__ == "__main__":
    main()
