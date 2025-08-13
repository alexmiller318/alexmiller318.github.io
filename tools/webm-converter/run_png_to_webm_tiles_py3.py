#!/usr/bin/env python3
"""
Python 3 Launcher for PNG to WebM Tiles Converter
This script ensures the main converter runs with Python 3
"""

import sys
import subprocess
import os

def main():
    # Check Python version
    if sys.version_info[0] < 3:
        print("Error: This script requires Python 3")
        print(f"Current Python version: {sys.version}")
        sys.exit(1)
    
    print(f"Python {sys.version_info[0]}.{sys.version_info[1]}.{sys.version_info[2]} detected")
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_script = os.path.join(script_dir, "png_sequence_to_webm_tiles.py")
    
    # Run the main script
    try:
        subprocess.run([sys.executable, main_script], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running main script: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nScript interrupted by user")
        sys.exit(0)

if __name__ == "__main__":
    main()
