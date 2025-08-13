#!/usr/bin/env python3
"""
Setup script to create a standalone macOS app for the WebM Tile Converter
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def install_dependencies():
    """Install required dependencies"""
    print("Installing required dependencies...")
    
    dependencies = [
        "pillow",
        "imageio[ffmpeg]",
        "numpy",
        "pyinstaller",
        "cairosvg"
    ]
    
    for dep in dependencies:
        print(f"Installing {dep}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", dep], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to install {dep}: {e}")
            return False
    
    return True

def create_app():
    """Create the macOS app bundle"""
    print("Creating macOS app bundle...")
    
    # PyInstaller command to create the app
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=WebM Tile Converter",
        "--icon=app_icon.icns",  # We'll create this
        "--add-data=README.md:.",
        "--hidden-import=PIL._tkinter_finder",
        "--hidden-import=tkinter",
        "--hidden-import=tkinter.filedialog",
        "--hidden-import=imageio",
        "--hidden-import=imageio.v3",
        "--hidden-import=numpy",
        "--hidden-import=cairosvg",
        "png_sequence_to_webm_tiles.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✅ App bundle created successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create app bundle: {e}")
        return False

def create_icon():
    """Create a simple app icon"""
    print("Creating app icon...")
    
    # Create a simple SVG icon
    svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#4A90E2;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#357ABD;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Background -->
  <rect width="512" height="512" rx="80" fill="url(#grad1)"/>
  
  <!-- Grid pattern representing tiles -->
  <g stroke="white" stroke-width="8" fill="none" opacity="0.9">
    <!-- Vertical lines -->
    <line x1="128" y1="64" x2="128" y2="448"/>
    <line x1="256" y1="64" x2="256" y2="448"/>
    <line x1="384" y1="64" x2="384" y2="448"/>
    
    <!-- Horizontal lines -->
    <line x1="64" y1="128" x2="448" y2="128"/>
    <line x1="64" y1="256" x2="448" y2="256"/>
    <line x1="64" y1="384" x2="448" y2="384"/>
  </g>
  
  <!-- Play button in center -->
  <polygon points="200,160 200,352 352,256" fill="white" opacity="0.9"/>
  
  <!-- Text -->
  <text x="256" y="480" text-anchor="middle" fill="white" font-family="Arial, sans-serif" font-size="24" font-weight="bold">
    WebM Tiles
  </text>
</svg>'''
    
    with open("app_icon.svg", "w") as f:
        f.write(svg_content)
    
    # Convert SVG to ICNS (we'll need to install iconutil or use a different approach)
    print("Icon created as SVG. You may need to convert it to ICNS manually.")
    return True

def create_readme():
    """Create a README file for the app"""
    readme_content = """# WebM Tile Converter

A powerful tool to convert animations and videos into custom-sized WebM tiles, perfect for creating Telegram emoji packs or other animated tile sets.

## Features

✅ **Multiple Input Formats:**
- PNG sequences (numbered PNG files)
- SVG sequences (numbered SVG files)
- Animated WebP files
- GIF animations
- MP4, AVI, MOV, WebM videos
- And any format FFmpeg supports

✅ **Automatic FPS Detection:**
- Detects original frame rate from source files
- Preserves original animation timing
- Manual override available

✅ **Custom Tile Sizing:**
- Choose any tile dimensions
- Automatic grid calculation
- Preview of tile layout

✅ **High Quality Output:**
- WebM format with VP9 codec
- Preserves transparency
- Optimized for Telegram emoji use

## How to Use

1. **Launch the app** by double-clicking "WebM Tile Converter"
2. **Select your input:**
   - For video/animation files: Choose the file directly
   - For PNG/SVG sequences: Cancel the file dialog, then select the folder containing numbered files
3. **Set frame duration:**
   - Use detected FPS (recommended)
   - Or choose from presets (10 FPS, 5 FPS, 2 FPS)
   - Or enter custom duration
4. **Choose tile size:**
   - Enter width and height in pixels
   - See suggested sizes for balanced grids
5. **Wait for processing:**
   - The app will create all tiles automatically
   - Output saved to Desktop/WEBM folder

## Input File Requirements

### PNG Sequences:
- Folder with numbered PNG files (1.png, 2.png, 10.png, etc.)
- All files must have same dimensions
- Files sorted numerically

### SVG Sequences:
- Folder with numbered SVG files (1.svg, 2.svg, 10.svg, etc.)
- All files must have same dimensions
- Files sorted numerically

### Video/Animation Files:
- Any format supported by FFmpeg
- MP4, AVI, MOV, WebM, GIF, WebP, etc.

## Output

- **Location:** Desktop/WEBM/[filename]_[timestamp]/
- **Format:** WebM files with VP9 codec
- **Naming:** [original_name]_Row[#]_Col[#].webm
- **Quality:** High quality with transparency support

## System Requirements

- macOS 10.14 or later
- 4GB RAM minimum (8GB recommended)
- 2GB free disk space
- FFmpeg (included in app bundle)

## Troubleshooting

**App won't start:**
- Make sure you're on macOS 10.14+
- Try right-clicking and selecting "Open" if blocked by Gatekeeper

**No file dialog appears:**
- Check if another app is blocking the dialog
- Try clicking on the app icon to bring it to front

**Conversion fails:**
- Ensure input files are valid
- Check available disk space
- Try with smaller tile sizes

**Slow performance:**
- Use smaller tile sizes
- Close other applications
- Ensure adequate RAM available

## Credits

Created with Python, FFmpeg, and PyInstaller.
Supports all major animation and video formats.

---
Made with ❤️ for the animation community
"""
    
    with open("README.md", "w") as f:
        f.write(readme_content)
    
    return True

def create_launcher_script():
    """Create a simple launcher script for easier distribution"""
    launcher_content = '''#!/bin/bash
# WebM Tile Converter Launcher
# This script launches the WebM Tile Converter app

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Launch the app
"$SCRIPT_DIR/WebM Tile Converter"

# Keep terminal open if there are errors
if [ $? -ne 0 ]; then
    echo "App exited with error code $?"
    read -p "Press Enter to close..."
fi
'''
    
    with open("launch_webm_converter.sh", "w") as f:
        f.write(launcher_content)
    
    # Make it executable
    os.chmod("launch_webm_converter.sh", 0o755)
    
    return True

def main():
    """Main setup function"""
    print("=== WebM Tile Converter App Setup ===")
    print("This will create a standalone macOS app that you can share with friends.")
    print()
    
    # Check if we're on macOS
    if sys.platform != "darwin":
        print("❌ This setup is designed for macOS only.")
        return False
    
    # Install dependencies
    if not install_dependencies():
        print("❌ Failed to install dependencies.")
        return False
    
    # Create supporting files
    create_icon()
    create_readme()
    create_launcher_script()
    
    # Create the app
    if not create_app():
        print("❌ Failed to create app bundle.")
        return False
    
    print()
    print("🎉 Setup complete!")
    print()
    print("Your app is ready:")
    print("- Main app: dist/WebM Tile Converter")
    print("- Launcher script: launch_webm_converter.sh")
    print("- Documentation: README.md")
    print()
    print("To share with friends:")
    print("1. Copy the 'dist/WebM Tile Converter' file")
    print("2. They can double-click to run it")
    print("3. Or use the launcher script for easier distribution")
    print()
    print("Note: Friends may need to right-click and 'Open' the first time")
    print("due to macOS security (not signed with Apple Developer ID)")
    
    return True

if __name__ == "__main__":
    main()
