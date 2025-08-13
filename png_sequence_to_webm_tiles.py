#!/usr/bin/env python3
"""
Universal Animation to Custom Size WebM Tiles (Telegram Emoji Ready)

This script converts any animation format (PNG sequence, WebP, GIF, MP4, etc.) 
directly into animated WebM tiles of your chosen size, preserving transparency.

Supported input formats:
- PNG sequence (folder of numbered PNG files)
- SVG sequence (folder of numbered SVG files)
- Animated WebP files
- GIF files
- MP4 files
- AVI files
- MOV files
- WebM files
- And any other format FFmpeg supports

Instructions:
1. Install Python dependencies:
   pip install pillow 'imageio[ffmpeg]' numpy cairosvg

2. Install ffmpeg (required for WebM conversion):
   - macOS: brew install ffmpeg
   - Ubuntu: sudo apt-get install ffmpeg
   - Windows: https://ffmpeg.org/download.html (add ffmpeg to PATH)

Usage:
    python png_sequence_to_webm_tiles.py

This script will prompt you to:
1. Select a file or folder containing animation files
2. Specify tile dimensions (width and height)
3. Set frame duration
Then output animated WebM tiles of your chosen size, preserving transparency.
"""

import os
import sys
import re
import glob
import math
import tempfile
import shutil
import subprocess
from PIL import Image
import imageio.v3 as iio
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import filedialog

def natural_sort_key(text):
    """Sort strings containing numbers naturally (1, 2, 10, 11, etc.)"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split('([0-9]+)', text)]

def get_tile_dimensions(animation_width=None, animation_height=None):
    """Prompt user for tile dimensions"""
    print("\n=== Tile Size Configuration ===")
    print("Enter the desired dimensions for your tiles.")
    print("Consider the total image size when choosing tile dimensions.")
    
    if animation_width and animation_height:
        print(f"\nAnimation dimensions: {animation_width}x{animation_height} pixels")
        
        # Suggest some reasonable tile sizes
        suggested_width = max(1, animation_width // 4)  # 4 columns
        suggested_height = max(1, animation_height // 4)  # 4 rows
        
        print(f"Suggested tile sizes for a balanced grid:")
        print(f"  - {suggested_width}x{suggested_height} (4x4 grid)")
        print(f"  - {max(1, animation_width//2)}x{max(1, animation_height//2)} (2x2 grid)")
        print(f"  - {max(1, animation_width//8)}x{max(1, animation_height//8)} (8x8 grid)")
    
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

def detect_fps_from_file(file_path):
    """Detect FPS from video/animation files using multiple methods"""
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Method 1: Try FFmpeg (works for most video formats)
    try:
        print("Detecting FPS using FFmpeg...")
        cmd = [
            "ffmpeg", "-i", file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.PIPE)
        
        if result.returncode != 0:  # FFmpeg always returns non-zero for -i, but stderr contains info
            stderr_output = result.stderr
            
            # Look for FPS information in the output
            fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', stderr_output, re.IGNORECASE)
            if fps_match:
                fps = float(fps_match.group(1))
                print(f"✅ Detected FPS: {fps}")
                return fps
            
            # Look for frame rate in stream info
            frame_rate_match = re.search(r'(\d+(?:\.\d+)?)\s*tbr', stderr_output, re.IGNORECASE)
            if frame_rate_match:
                fps = float(frame_rate_match.group(1))
                print(f"✅ Detected frame rate: {fps} FPS")
                return fps
                
    except Exception as e:
        print(f"FFmpeg FPS detection failed: {e}")
    
    # Method 2: Try imageio for animated formats (GIF, WebP, etc.)
    try:
        print("Trying imageio for FPS detection...")
        import imageio.v3 as iio
        
        # Get metadata from the file
        metadata = iio.immeta(file_path)
        if metadata and 'fps' in metadata:
            fps = float(metadata['fps'])
            print(f"✅ Detected FPS from imageio: {fps}")
            return fps
            
        # For GIF files, try to get duration info
        if file_ext == '.gif':
            with Image.open(file_path) as img:
                if hasattr(img, 'info') and 'duration' in img.info:
                    duration_ms = img.info['duration']
                    if duration_ms > 0:
                        fps = 1000 / duration_ms
                        print(f"✅ Detected FPS from GIF duration: {fps:.2f}")
                        return fps
                        
    except Exception as e:
        print(f"imageio FPS detection failed: {e}")
    
    # Method 3: Try using exiftool if available
    try:
        print("Trying exiftool for FPS detection...")
        cmd = ["exiftool", "-FrameRate", "-b", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            fps = float(result.stdout.strip())
            print(f"✅ Detected FPS from exiftool: {fps}")
            return fps
    except (subprocess.CalledProcessError, FileNotFoundError, ValueError):
        pass  # exiftool not available or no FPS data
    
    print("❌ Could not automatically detect FPS from file")
    return None

def get_frame_duration(detected_fps=None):
    """Prompt user for frame duration or use detected FPS"""
    if detected_fps:
        print(f"\n=== Frame Duration Configuration ===")
        print(f"✅ Detected original FPS: {detected_fps:.2f}")
        print(f"   This gives a frame duration of {1000/detected_fps:.1f}ms")
        
        response = input("Use detected FPS? (y/n, default y): ").strip().lower()
        if response != 'n':
            duration = 1000 / detected_fps
            print(f"Using detected FPS: {detected_fps:.2f} ({duration:.1f}ms per frame)")
            return duration
    
    print("\n=== Frame Duration Configuration ===")
    print("Enter the duration for each frame in milliseconds.")
    print("Common presets:")
    print("  - 1: 100ms = 10 FPS (fast animation)")
    print("  - 2: 200ms = 5 FPS (medium animation)")
    print("  - 3: 500ms = 2 FPS (slow animation)")
    print("  - 4: Custom duration")
    
    while True:
        try:
            choice = input("Choose preset or enter custom duration (1-4, default 2): ").strip()
            
            if not choice:
                duration = 200
                break
            elif choice == "1":
                duration = 100
                break
            elif choice == "2":
                duration = 200
                break
            elif choice == "3":
                duration = 500
                break
            elif choice == "4":
                custom_duration = input("Enter custom duration in milliseconds: ").strip()
                duration = int(custom_duration)
                if duration <= 0:
                    print("Duration must be a positive number. Please try again.")
                    continue
                break
            else:
                # Try to parse as direct duration input
                duration = int(choice)
                if duration <= 0:
                    print("Duration must be a positive number. Please try again.")
                    continue
                break
                
        except ValueError:
            print("Please enter a valid number or preset choice (1-4).")
    
    fps = 1000 / duration
    print(f"\nFrame duration set to: {duration}ms ({fps:.1f} FPS)")
    return duration

def select_input():
    """Open file/folder selection dialog"""
    print("\n=== Input Selection ===")
    print("Select a file (WebP, GIF, MP4, etc.) or folder (PNG sequence)")
    
    root = tk.Tk()
    root.withdraw()
    
    # Try to bring the dialog to front
    root.lift()
    root.attributes('-topmost', True)
    root.attributes('-topmost', False)
    
    # First try to select a file
    file_path = filedialog.askopenfilename(
        title="Select animation file (WebP, GIF, MP4, WebM, SVG, etc.) or Cancel to select folder",
        filetypes=[
            ("All supported formats", "*.webp;*.gif;*.mp4;*.avi;*.mov;*.mkv;*.flv;*.webm;*.svg"),
            ("WebP files", "*.webp"),
            ("GIF files", "*.gif"),
            ("MP4 files", "*.mp4"),
            ("AVI files", "*.avi"),
            ("MOV files", "*.mov"),
            ("WebM files", "*.webm"),
            ("SVG files", "*.svg"),
            ("All files", "*.*")
        ]
    )
    
    if file_path:
        print(f"Selected file: {file_path}")
        return file_path, "file"
    
    # If no file selected, try folder selection
    print("\nNo file selected. Trying folder selection for PNG sequence...")
    folder_path = filedialog.askdirectory(
        title="Select folder containing PNG sequence files"
    )
    
    if folder_path:
        print(f"Selected folder: {folder_path}")
        return folder_path, "folder"
    
    print("\nNo file or folder selected. You can manually enter the path:")
    manual_path = input("Enter the full path to your file or folder: ").strip()
    if manual_path:
        if os.path.isfile(manual_path):
            return manual_path, "file"
        elif os.path.isdir(manual_path):
            return manual_path, "folder"
        else:
            print("Invalid path provided. Exiting.")
            sys.exit(1)
    else:
        print("No path provided. Exiting.")
        sys.exit(1)

def is_png_sequence(folder_path):
    """Check if folder contains PNG sequence files"""
    png_pattern = os.path.join(folder_path, "*.png")
    png_files = glob.glob(png_pattern)
    return len(png_files) > 0

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

def is_svg_sequence(folder_path):
    """Check if folder contains SVG sequence files"""
    svg_pattern = os.path.join(folder_path, "*.svg")
    svg_files = glob.glob(svg_pattern)
    return len(svg_files) > 0

def get_svg_files(folder_path):
    """Get all SVG files from the folder, sorted naturally"""
    svg_pattern = os.path.join(folder_path, "*.svg")
    svg_files = glob.glob(svg_pattern)
    
    if not svg_files:
        print(f"No SVG files found in {folder_path}")
        sys.exit(1)
    
    # Sort files naturally (1.svg, 2.svg, 10.svg, etc.)
    svg_files.sort(key=natural_sort_key)
    
    print(f"Found {len(svg_files)} SVG files:")
    for i, file in enumerate(svg_files[:5]): # Show first 5 files
        print(f"  {os.path.basename(file)}")
    if len(svg_files) > 5:
        print(f"  ... and {len(svg_files) - 5} more files")
    
    return svg_files

def convert_to_png_sequence(input_path, input_type):
    """Convert any input format to PNG sequence"""
    print(f"\nConverting {input_type} to PNG sequence...")
    
    temp_dir = tempfile.mkdtemp()
    temp_png_files = []
    
    try:
        if input_type == "file":
            # Convert single file to PNG sequence
            print(f"Extracting frames from {os.path.basename(input_path)}...")
            
            # Use FFmpeg to extract frames
            output_pattern = os.path.join(temp_dir, "frame_%04d.png")
            cmd = [
                "ffmpeg", "-y",
                "-i", input_path,
                "-vf", "fps=30",  # Default 30 FPS, will be adjusted later
                "-pix_fmt", "rgba",
                output_pattern
            ]
            
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            # Get the list of generated PNG files
            temp_png_files = sorted(glob.glob(os.path.join(temp_dir, "frame_*.png")))
            
            if not temp_png_files:
                print("No frames extracted. Trying alternative method...")
                return convert_to_png_sequence_alternative(input_path, temp_dir)
            
            print(f"Extracted {len(temp_png_files)} frames")
            
        elif input_type == "folder":
            # Check if folder contains PNG or SVG sequences
            if is_png_sequence(input_path):
                # Copy PNG files from folder
                png_files = get_png_files(input_path)
                for i, png_file in enumerate(png_files):
                    temp_png_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                    with Image.open(png_file) as img:
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                        img.save(temp_png_path, "PNG")
                    temp_png_files.append(temp_png_path)
            elif is_svg_sequence(input_path):
                # Convert SVG files to PNG sequence
                svg_files = get_svg_files(input_path)
                print(f"Converting {len(svg_files)} SVG files to PNG sequence...")
                
                # We'll need to install cairosvg for SVG support
                try:
                    import cairosvg
                    for i, svg_file in enumerate(svg_files):
                        temp_png_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                        # Convert SVG to PNG using cairosvg
                        cairosvg.svg2png(url=svg_file, write_to=temp_png_path, output_width=1024, output_height=1024)
                        temp_png_files.append(temp_png_path)
                    print(f"Successfully converted {len(temp_png_files)} SVG files to PNG")
                except ImportError:
                    print("SVG support requires cairosvg. Installing...")
                    try:
                        subprocess.run([sys.executable, "-m", "pip", "install", "cairosvg"], check=True)
                        import cairosvg
                        for i, svg_file in enumerate(svg_files):
                            temp_png_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                            cairosvg.svg2png(url=svg_file, write_to=temp_png_path, output_width=1024, output_height=1024)
                            temp_png_files.append(temp_png_path)
                        print(f"Successfully converted {len(temp_png_files)} SVG files to PNG")
                    except Exception as e:
                        print(f"Failed to install cairosvg: {e}")
                        print("SVG conversion failed. Please install manually: pip install cairosvg")
                        return None, None
            else:
                print("No PNG or SVG sequence files found in the selected folder.")
                return None, None
        
        return temp_png_files, temp_dir
        
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        print("Trying alternative conversion method...")
        return convert_to_png_sequence_alternative(input_path, temp_dir)
    except Exception as e:
        print(f"Error during conversion: {e}")
        return None, None

def convert_to_png_sequence_alternative(input_path, temp_dir):
    """Alternative conversion method using PIL/imageio that is robust for both static and animated inputs.
    Uses imageio.v3.imiter to iterate frames safely. Falls back to PIL for single images.
    """
    try:
        print("Using alternative conversion method...")

        temp_png_files = []

        # Prefer an iterator over frames; this works for WebP/GIF/MP4/etc. If the
        # input is static, imiter will still yield exactly one frame.
        try:
            frame_iter = iio.imiter(input_path)
            got_any = False
            for i, frame in enumerate(frame_iter):
                got_any = True
                # frame is a numpy array (H, W, C) or (H, W); normalize to RGBA
                if frame.ndim == 3:
                    if frame.shape[2] == 4:
                        pil_img = Image.fromarray(frame)
                    elif frame.shape[2] == 3:
                        pil_img = Image.fromarray(frame).convert('RGBA')
                    else:
                        pil_img = Image.fromarray(frame).convert('RGBA')
                else:
                    pil_img = Image.fromarray(frame).convert('RGBA')

                temp_png_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                pil_img.save(temp_png_path, "PNG")
                temp_png_files.append(temp_png_path)

            if got_any:
                print(f"Extracted {len(temp_png_files)} frames using imiter")
                return temp_png_files, temp_dir
        except Exception as e:
            print(f"imageio.imiter failed or not applicable: {e}")

        # Fallback: read as a single image (spritesheet or still) with PIL
        with Image.open(input_path) as img:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            temp_png_path = os.path.join(temp_dir, "frame_0000.png")
            img.save(temp_png_path, "PNG")
            print("Input treated as a single-frame image; created one PNG frame.")
            return [temp_png_path], temp_dir

    except Exception as e:
        print(f"Alternative conversion failed: {e}")
        return None, None

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

def load_png_sequence(png_files):
    """Load all PNG files as frames"""
    print(f"\nLoading {len(png_files)} PNG files...")
    frames = []
    
    for i, png_file in enumerate(png_files):
        try:
            with Image.open(png_file) as img:
                # Ensure RGBA format for transparency
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                frames.append(np.array(img))
            
            # Progress indicator
            if (i + 1) % 10 == 0 or i + 1 == len(png_files):
                print(f"  Loaded {i + 1}/{len(png_files)} frames...")
                
        except Exception as e:
            print(f"Error loading {os.path.basename(png_file)}: {e}")
            return None
    
    print(f"Successfully loaded {len(frames)} frames")
    return frames

def crop_frames(frames, x, y, width, height):
    """Crop frames to the specified region (x, y, width, height).
    If the crop extends outside the frame, pad with transparent pixels to keep consistent tile size.
    """
    cropped = []
    for frame in frames:
        pil = Image.fromarray(frame)
        W, H = pil.size
        # If the tile starts outside the image, create a fully transparent tile
        if x >= W or y >= H:
            empty = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            cropped.append(np.array(empty))
            continue
        # Compute safe crop box within the source
        x2 = min(x + width, W)
        y2 = min(y + height, H)
        tile = pil.crop((x, y, x2, y2))
        # If the crop was smaller (near edges), paste onto a transparent canvas
        if tile.size != (width, height):
            canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            canvas.paste(tile, (0, 0))
            tile = canvas
        cropped.append(np.array(tile))
    return cropped

def save_frames_as_webm(frames, output_path, fps, tile_width, tile_height):
    """Save frames directly as WebM using FFmpeg.
    Ensures even dimensions for yuva420p by padding, avoids hard-coded duration caps.
    """
    temp_dir = tempfile.mkdtemp()
    temp_png_files = []

    try:
        # Save frames as PNG sequence
        print(f"  Preparing {len(frames)} frames for WebM conversion...")
        for i, frame in enumerate(frames):
            temp_png_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
            pil_img = Image.fromarray(frame)
            pil_img.save(temp_png_path, "PNG")
            temp_png_files.append(temp_png_path)

        # Even-dimension padding for yuva420p (required by VP9 in many cases)
        # We scale to the requested tile size, then pad to the next even numbers.
        input_pattern = os.path.join(temp_dir, "frame_%04d.png")
        vf = f"scale={tile_width}:{tile_height}:flags=lanczos,pad=ceil(iw/2)*2:ceil(ih/2)*2"

        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", input_pattern,
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            "-an",
            "-vf", vf,
            "-auto-alt-ref", "0",
            "-b:v", "2M",
            output_path
        ]

        print(f"  Converting to WebM...")
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e}")
        print(f"FFmpeg stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Error during WebM conversion: {e}")
        return False
    finally:
        # Clean up temporary files and directory
        for temp_file in temp_png_files:
            if os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except:
                    pass
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass

def get_tile_name(base, row, col):
    return f"{base}_Row{row+1}_Col{col+1}.webm"

def main():
    print("=== Universal Animation to Custom Size WebM Tiles ===")
    print("Supports: PNG sequences, SVG sequences, WebP, GIF, MP4, AVI, MOV, WebM, and more!\n")
    
    # Select input file or folder FIRST
    input_path, input_type = select_input()
    
    # Convert to PNG sequence if needed
    png_files, temp_dir = convert_to_png_sequence(input_path, input_type)
    if png_files is None:
        print("Failed to convert input to PNG sequence. Exiting.")
        sys.exit(1)
    
    # Validate images
    if not validate_images(png_files):
        print("Image validation failed. Exiting.")
        sys.exit(1)
    
    # Load all PNG files as frames to get dimensions
    frames = load_png_sequence(png_files)
    if frames is None:
        print("Failed to load PNG sequence. Exiting.")
        sys.exit(1)
    
    # Get dimensions from the first frame (numpy shape is height, width, channels)
    height, width = frames[0].shape[:2]
    print(f"\nLoaded sequence: {len(frames)} frames, {width}x{height} pixels")
    
    # Debug: Check the actual shape
    print(f"Debug: First frame shape: {frames[0].shape}")
    print(f"Debug: Interpreting as width={width}, height={height}")
    
    # Detect FPS from source file if possible, then get frame duration
    detected_fps = None
    if input_type == "file":
        detected_fps = detect_fps_from_file(input_path)
    
    # NOW get frame duration from user (with context about the sequence)
    frame_duration = get_frame_duration(detected_fps)
    
    # NOW get tile dimensions from user (with context about the sequence)
    tile_width, tile_height = get_tile_dimensions(width, height)
    
    # Calculate grid dimensions
    n_rows = math.ceil(height / tile_height)
    n_cols = math.ceil(width / tile_width)
    fps = 1000 / frame_duration
    
    print(f"\nProcessing {n_rows}x{n_cols} grid of {tile_width}x{tile_height} tiles...")
    
    # Warn about unusual grid layouts
    if n_cols == 1 and n_rows > 1:
        print(f"⚠️  Note: Your animation is very narrow ({width}px wide). With {tile_width}px tiles, you'll get only 1 column.")
        print(f"   Consider using smaller tile width (e.g., {max(1, width//2)}px) for more columns.")
    elif n_rows == 1 and n_cols > 1:
        print(f"⚠️  Note: Your animation is very short ({height}px tall). With {tile_height}px tiles, you'll get only 1 row.")
        print(f"   Consider using smaller tile height (e.g., {max(1, height//2)}px) for more rows.")
    elif n_cols == 1 and n_rows == 1:
        print(f"⚠️  Note: Your tile size ({tile_width}x{tile_height}) is larger than the animation ({width}x{height}).")
        print(f"   The entire animation will be scaled to fit in a single tile.")
    
    # Ask user if they want to continue or adjust tile size
    if n_cols == 1 or n_rows == 1:
        response = input("\nContinue with current tile size? (y/n): ").lower().strip()
        if response != 'y':
            print("Please run the script again with different tile dimensions.")
            sys.exit(0)
    
    # Prepare output folder
    if input_type == "file":
        base_name = os.path.splitext(os.path.basename(input_path))[0]
    else:
        base_name = os.path.basename(input_path)
    
    now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_folder = f"/Users/alexmiller/Desktop/WEBM/{base_name}_{now_str}"
    os.makedirs(out_folder, exist_ok=True)
    
    # Process each tile
    for row in range(n_rows):
        for col in range(n_cols):
            x = col * tile_width
            y = row * tile_height
            
            print(f"Creating tile {row+1}x{col+1}: {get_tile_name(base_name, row, col)}")
            
            # Crop frames for this tile
            cropped = crop_frames(frames, x, y, tile_width, tile_height)
            
            # Save as WebM
            out_name = get_tile_name(base_name, row, col)
            out_path = os.path.join(out_folder, out_name)
            
            success = save_frames_as_webm(cropped, out_path, fps, tile_width, tile_height)
            if not success:
                print(f"Failed to create tile {out_name}")
    
    # Clean up temporary directory if it was created
    if temp_dir and os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass  # Don't fail if cleanup doesn't work
    
    print(f"\n✅ All tiles saved to: {out_folder}")

if __name__ == "__main__":
    main()
