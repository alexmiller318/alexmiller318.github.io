#!/usr/bin/env python3
"""
Animated MP4 to Custom Size WebM Tiles (Telegram Emoji Ready)

Instructions:
1. Install Python dependencies:
   pip install pillow 'imageio[ffmpeg]' numpy

2. Install ffmpeg (required for WebM conversion):
   - macOS: brew install ffmpeg
   - Ubuntu: sudo apt-get install ffmpeg
   - Windows: https://ffmpeg.org/download.html (add ffmpeg to PATH)

Usage:
    python split_webp_to_webm_tiles.py

This script will prompt you to select an MP4 file and specify tile dimensions, then output animated WebM tiles of your chosen size, preserving transparency, in a new folder on your Desktop named after the input file and the current date/time.
"""

import os
import sys
import math
import tempfile
import subprocess
from PIL import Image
import imageio.v3 as iio
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

def get_tile_name(base, row, col):
    return f"{base}_Row{row+1}_Col{col+1}.webm"

def crop_frames(frames, x, y, width, height):
    cropped = []
    for frame in frames:
        pil = Image.fromarray(frame)
        tile = pil.crop((x, y, x+width, y+height))
        cropped.append(np.array(tile))
    return cropped

def save_frames_as_mp4(frames, durations, out_path, fps):
    """Save frames as MP4 using FFmpeg"""
    temp_dir = tempfile.mkdtemp()
    temp_png_files = []
    
    try:
        # Save frames as PNG sequence
        for i, frame in enumerate(frames):
            temp_png_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            pil_img = Image.fromarray(frame)
            pil_img.save(temp_png_path, "PNG")
            temp_png_files.append(temp_png_path)
        
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
            out_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
    finally:
        # Clean up temporary files
        for temp_file in temp_png_files:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)

def convert_mp4_to_webm(mp4_path, webm_path, fps, tile_width, tile_height):
    cmd = [
        "ffmpeg", "-y",
        "-i", mp4_path,
        "-c:v", "libvpx-vp9",
        "-pix_fmt", "yuva420p",
        "-an",
        "-r", str(fps),
        "-vf", f"scale={tile_width}:{tile_height}:flags=lanczos",
        "-t", "3",
        "-auto-alt-ref", "0",
        "-b:v", "2M",  # Set bitrate for better quality
        webm_path
    ]
    
    # Run ffmpeg with error handling
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return False

def get_tile_dimensions():
    """Prompt user for tile dimensions"""
    print("\n=== Tile Size Configuration ===")
    print("Enter the desired dimensions for your tiles.")
    
    while True:
        try:
            width = input("Enter tile width (in pixels): ").strip()
            if not width:
                print("Width cannot be empty. Please try again.")
                continue
            width = int(width)
            if width <= 0:
                print("Width must be a positive number. Please try again.")
                continue
            break
        except ValueError:
            print("Please enter a valid number for width.")
    
    while True:
        try:
            height = input("Enter tile height (in pixels): ").strip()
            if not height:
                print("Height cannot be empty. Please try again.")
                continue
            height = int(height)
            if height <= 0:
                print("Height must be a positive number. Please try again.")
                continue
            break
        except ValueError:
            print("Please enter a valid number for height.")
    
    print(f"\nTile size set to: {width}x{height} pixels")
    return width, height

def load_frames_and_durations(path):
    """Robustly load frames (WebP/MP4/etc.) and per-frame durations.
    Ensures we're treating the first dimension as frames, not width/height.
    """
    frames = []
    durations = []

    # Primary path: iterate frames with imageio's iterator
    try:
        for img in iio.imiter(path):
            frames.append(np.array(img))
        # Try to read per-frame metadata durations (ms)
        try:
            with iio.imopen(path, 'r') as rdr:
                try:
                    n = len(rdr)  # type: ignore[reportUnknownArgumentType]
                except Exception:
                    n = len(frames)
                for i in range(n):
                    try:
                        meta = rdr.metadata(index=i)
                        durations.append(meta.get('duration', 100))
                    except Exception:
                        durations.append(100)
        except Exception:
            pass
    except Exception:
        pass

    # Fallback: single array read
    if not frames:
        arr = iio.imread(path)
        if getattr(arr, 'ndim', 0) == 4:
            # shape: (num_frames, H, W, C)
            frames = [frame for frame in arr]
        elif getattr(arr, 'ndim', 0) >= 2:
            # single image
            frames = [arr]
        else:
            raise RuntimeError("Could not read any frames from input.")
        durations = [100] * len(frames)

    # Safety: if we failed to get durations, default
    if not durations or len(durations) != len(frames):
        durations = [100] * len(frames)

    return frames, durations

def main():
    # Get tile dimensions from user
    tile_width, tile_height = get_tile_dimensions()
    
    # File browser dialog
    root = tk.Tk()
    root.withdraw()
    in_path = filedialog.askopenfilename(
        title="Select input file (MP4 or WebP)",
        filetypes=[
            ("Supported", "*.mp4 *.webp"),
            ("MP4 files", "*.mp4"),
            ("WebP files", "*.webp"),
            ("All files", "*.*"),
        ]
    )
    if not in_path:
        print("No file selected. Exiting.")
        sys.exit(1)
    base = os.path.splitext(os.path.basename(in_path))[0]

    # Prepare output folder
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_folder = f"/Users/alexmiller/Desktop/WEBM/{base}_{now_str}"
    os.makedirs(out_folder, exist_ok=True)

    # Read frames and durations robustly (handles WebP/MP4 correctly)
    frames, durations = load_frames_and_durations(in_path)

    if not frames:
        print("No frames found in the input file.")
        sys.exit(1)

    # Determine dimensions from the first frame (H, W, C)
    h, w = frames[0].shape[:2]

    # Debug prints to help diagnose incorrect dimension reads
    print(f"Loaded {len(frames)} frame(s). First frame shape: {frames[0].shape}")
    print(f"Detected canvas size: {w}x{h} (WxH)")

    n_rows = math.ceil(h / tile_height)
    n_cols = math.ceil(w / tile_width)

    print(f"Tiling grid will be {n_rows} row(s) × {n_cols} column(s) for tiles of {tile_width}×{tile_height}.")

    # Derive FPS from first frame duration if available (duration in ms)
    try:
        first_ms = max(1, int(durations[0]))
        fps = max(1, min(30, round(1000 / first_ms)))
    except Exception:
        fps = 15

    print(f"\nProcessing {n_rows}x{n_cols} grid of {tile_width}x{tile_height} tiles...")

    for row in range(n_rows):
        for col in range(n_cols):
            x = col * tile_width
            y = row * tile_height
            cropped = crop_frames(frames, x, y, tile_width, tile_height)
            # Save to temp webp
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                save_frames_as_mp4(cropped, durations, tmp.name, fps)
                tmp.flush()
                out_name = get_tile_name(base, row, col)
                out_path = os.path.join(out_folder, out_name)
                print(f"Creating tile {row+1}x{col+1}: {out_name}")
                success = convert_mp4_to_webm(tmp.name, out_path, fps, tile_width, tile_height)
                if not success:
                    print(f"Failed to create tile {out_name}")
            os.unlink(tmp.name)
    print(f"All tiles saved to: {out_folder}")

if __name__ == "__main__":
    main() 