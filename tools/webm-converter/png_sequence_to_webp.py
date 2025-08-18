#!/usr/bin/env python3
"""
PNG Sequence to FFmpeg-Compatible MP4 Converter

This script converts a folder of PNG sequence files (numbered 1, 2, 3, etc.) 
into a single MP4 file that's fully compatible with FFmpeg for further processing.

Instructions:
1. Install Python dependencies:
   pip install pillow

Usage:
    python png_sequence_to_webp.py

This script will prompt you to select a folder containing PNG sequence files,
then convert them into an MP4 file with customizable frame duration
that's fully compatible with FFmpeg for tile creation.
"""

import os
import sys
import re
import glob
import tempfile
import subprocess
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime

def natural_sort_key(text):
    """Sort strings containing numbers naturally (1, 2, 10, 11, etc.)"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', text)]

def get_frame_duration():
    """Prompt user for frame duration"""
    print("\n=== Frame Duration Configuration ===")
    print("Enter the duration for each frame in milliseconds.")
    print("Common values:")
    print("  - 100ms = 10 FPS (fast animation)")
    print("  - 200ms = 5 FPS (medium animation)")
    print("  - 500ms = 2 FPS (slow animation)")
    
    while True:
        try:
            duration = input("Enter frame duration (in milliseconds, default 200): ").strip()
            if not duration:
                duration = 200
            else:
                duration = int(duration)
            
            if duration <= 0:
                print("Duration must be a positive number. Please try again.")
                continue
            break
        except ValueError:
            print("Please enter a valid number for duration.")
    
    print(f"\nFrame duration set to: {duration}ms")
    return duration

def select_folder():
    """Open folder selection dialog"""
    print("\n=== Folder Selection ===")
    print("A folder selection dialog should appear. If it doesn't appear,")
    print("you can also manually enter the path to your PNG sequence folder.")
    
    root = tk.Tk()
    root.withdraw()
    
    # Try to bring the dialog to front
    root.lift()
    root.attributes('-topmost', True)
    root.attributes('-topmost', False)
    
    folder_path = filedialog.askdirectory(
        title="Select folder containing PNG sequence files"
    )
    
    if not folder_path:
        print("\nNo folder selected via dialog. You can manually enter the path:")
        manual_path = input("Enter the full path to your PNG sequence folder: ").strip()
        if manual_path and os.path.isdir(manual_path):
            folder_path = manual_path
        else:
            print("Invalid path or no path provided. Exiting.")
            sys.exit(1)
    
    print(f"Selected folder: {folder_path}")
    return folder_path

def get_png_files(folder_path):
    """Get all PNG files from the folder, sorted naturally"""
    png_pattern = os.path.join(folder_path, "*.png")
    png_files = glob.glob(png_pattern)
    
    if not png_files:
        print(f"No PNG files found in {folder_path}")
        sys.exit(1)
    
    # Sort files naturally (1.png, 2.png, 10.png, etc.)
    png_files.sort(key=natural_sort_key)
    
    print(f"Found {len(png_files)} PNG files:")
    for i, file in enumerate(png_files[:5]):  # Show first 5 files
        print(f"  {os.path.basename(file)}")
    if len(png_files) > 5:
        print(f"  ... and {len(png_files) - 5} more files")
    
    return png_files

def validate_images(png_files):
    """Validate that all images have the same dimensions"""
    if not png_files:
        return False
    
    # Get dimensions of first image
    with Image.open(png_files[0]) as img:
        first_width, first_height = img.size
        print(f"\nImage dimensions: {first_width}x{first_height}")
    
    # Check all other images
    for i, file_path in enumerate(png_files[1:], 1):
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                if width != first_width or height != first_height:
                    print(f"Warning: {os.path.basename(file_path)} has different dimensions ({width}x{height})")
                    print("All images should have the same dimensions for best results.")
                    response = input("Continue anyway? (y/n): ").lower().strip()
                    if response != 'y':
                        return False
        except Exception as e:
            print(f"Error reading {os.path.basename(file_path)}: {e}")
            return False
    
    return True

def convert_sequence_to_mp4(png_files, frame_duration, output_path):
    """Convert PNG sequence to MP4 using FFmpeg directly"""
    print(f"\nConverting {len(png_files)} PNG files to MP4...")
    
    # Create temporary directory for PNG files
    temp_dir = tempfile.mkdtemp()
    temp_png_files = []
    
    try:
        # Copy PNG files to temp directory with sequential naming
        for i, png_file in enumerate(png_files):
            temp_png_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            with Image.open(png_file) as img:
                # Ensure RGBA format for transparency
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                img.save(temp_png_path, "PNG")
            temp_png_files.append(temp_png_path)
            
            # Progress indicator
            if (i + 1) % 10 == 0 or i + 1 == len(png_files):
                print(f"  Prepared {i + 1}/{len(png_files)} frames...")
        
        # Calculate FPS from frame duration
        fps = 1000 / frame_duration
        
        # Use FFmpeg to create MP4
        input_pattern = os.path.join(temp_dir, "frame_%04d.png")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", input_pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "medium",
            "-crf", "23",
            "-movflags", "+faststart",
            output_path
        ]
        
        print(f"Creating MP4 with FFmpeg (FPS: {fps:.1f})...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        print("Conversion completed successfully!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error during conversion: {e}")
        return False
    finally:
        # Clean up temporary files
        for temp_file in temp_png_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

def main():
    print("=== PNG Sequence to FFmpeg-Compatible MP4 Converter ===\n")
    
    # Get frame duration from user
    frame_duration = get_frame_duration()
    
    # Select folder containing PNG files
    folder_path = select_folder()
    
    # Get PNG files from the folder
    png_files = get_png_files(folder_path)
    
    # Validate images
    if not validate_images(png_files):
        print("Image validation failed. Exiting.")
        sys.exit(1)
    
    # Prepare output path
    folder_name = os.path.basename(folder_path)
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_filename = f"{folder_name}_{now_str}.mp4"
    
    # Ask user for output location
    root = tk.Tk()
    root.withdraw()
    output_path = filedialog.asksaveasfilename(
        title="Save MP4 as",
        defaultextension=".mp4",
        initialfile=output_filename,
        filetypes=[("MP4 files", "*.mp4")]
    )
    
    if not output_path:
        print("No output location selected. Exiting.")
        sys.exit(1)
    
    # Convert sequence to MP4 using FFmpeg
    success = convert_sequence_to_mp4(png_files, frame_duration, output_path)
    
    if success:
        print(f"\n✅ Successfully created FFmpeg-compatible MP4: {output_path}")
        print(f"📁 You can now use this MP4 file with the tile cropper script!")
    else:
        print("\n❌ Conversion failed. Please check the error messages above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
