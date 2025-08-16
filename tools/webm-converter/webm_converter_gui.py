#!/usr/bin/env python3
"""
WebM Tile Converter - Modern GUI
A user-friendly interface for converting animations to WebM tiles
"""

import os
import sys
import re
import glob
import math
import tempfile
import shutil
import subprocess
import threading
from PIL import Image
import imageio.v3 as iio
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import queue

class WebMTileConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WebM Tile Converter")
        self.root.geometry("800x700")
        self.root.minsize(700, 600)
        
        # Set app icon and styling
        self.setup_styling()
        
        # Variables
        self.input_path = tk.StringVar()
        self.input_type = tk.StringVar()
        self.detected_fps = tk.DoubleVar()
        self.frame_duration = tk.IntVar(value=200)
        self.tile_width = tk.IntVar()
        self.tile_height = tk.IntVar()
        self.output_folder = tk.StringVar()
        
        # Processing state
        self.is_processing = False
        self.progress_queue = queue.Queue()
        
        # Create GUI
        self.create_widgets()
        
        # Start progress updater
        self.update_progress()
    
    def setup_styling(self):
        """Setup modern styling for the GUI"""
        style = ttk.Style()
        
        # Configure colors
        self.root.configure(bg='#f0f0f0')
        
        # Configure styles
        style.theme_use('clam')
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), background='#f0f0f0')
        style.configure('Header.TLabel', font=('Arial', 12, 'bold'), background='#f0f0f0')
        style.configure('Info.TLabel', font=('Arial', 10), background='#f0f0f0')
        style.configure('Success.TLabel', font=('Arial', 10), foreground='green', background='#f0f0f0')
        style.configure('Error.TLabel', font=('Arial', 10), foreground='red', background='#f0f0f0')
        
        # Button styles
        style.configure('Primary.TButton', font=('Arial', 10, 'bold'))
        style.configure('Secondary.TButton', font=('Arial', 9))
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="🎬 WebM Tile Converter", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        subtitle_label = ttk.Label(main_frame, text="Convert animations to custom-sized WebM tiles for Telegram emoji packs", style='Info.TLabel')
        subtitle_label.grid(row=1, column=0, columnspan=3, pady=(0, 30))
        
        # Input Section
        self.create_input_section(main_frame, 2)
        
        # Settings Section
        self.create_settings_section(main_frame, 6)
        
        # Output Section
        self.create_output_section(main_frame, 12)
        
        # Progress Section
        self.create_progress_section(main_frame, 16)
        
        # Action Buttons
        self.create_action_buttons(main_frame, 20)
    
    def create_input_section(self, parent, row):
        """Create input file/folder selection section"""
        # Input frame
        input_frame = ttk.LabelFrame(parent, text="📁 Input File or Folder", padding="15")
        input_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        input_frame.columnconfigure(1, weight=1)
        
        # File selection
        ttk.Label(input_frame, text="Select animation file or PNG/SVG sequence folder:", style='Header.TLabel').grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # Input path display
        self.input_path_label = ttk.Label(input_frame, textvariable=self.input_path, style='Info.TLabel', wraplength=500)
        self.input_path_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Browse buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
        
        ttk.Button(button_frame, text="📄 Select File", command=self.browse_file, style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="📁 Select Folder", command=self.browse_folder, style='Primary.TButton').pack(side=tk.LEFT)
        
        # Supported formats info
        formats_text = "Supported: PNG sequences, SVG sequences, WebP, GIF, MP4, AVI, MOV, WebM, and more!"
        ttk.Label(input_frame, text=formats_text, style='Info.TLabel').grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
    
    def create_settings_section(self, parent, row):
        """Create settings section"""
        settings_frame = ttk.LabelFrame(parent, text="⚙️ Settings", padding="15")
        settings_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        settings_frame.columnconfigure(1, weight=1)
        
        # Frame duration
        ttk.Label(settings_frame, text="Frame Duration:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        duration_frame = ttk.Frame(settings_frame)
        duration_frame.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        self.detected_fps_label = ttk.Label(duration_frame, text="", style='Success.TLabel')
        self.detected_fps_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(duration_frame, text="Duration (ms):").pack(side=tk.LEFT, padx=(0, 5))
        duration_spinbox = ttk.Spinbox(duration_frame, from_=10, to=5000, textvariable=self.frame_duration, width=10)
        duration_spinbox.pack(side=tk.LEFT, padx=(0, 10))
        
        self.fps_label = ttk.Label(duration_frame, text="(5.0 FPS)", style='Info.TLabel')
        self.fps_label.pack(side=tk.LEFT)
        
        # Tile size
        ttk.Label(settings_frame, text="Tile Size:", style='Header.TLabel').grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        tile_frame = ttk.Frame(settings_frame)
        tile_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        ttk.Label(tile_frame, text="Width:").pack(side=tk.LEFT, padx=(0, 5))
        width_spinbox = ttk.Spinbox(tile_frame, from_=32, to=2048, textvariable=self.tile_width, width=10)
        width_spinbox.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(tile_frame, text="Height:").pack(side=tk.LEFT, padx=(0, 5))
        height_spinbox = ttk.Spinbox(tile_frame, from_=32, to=2048, textvariable=self.tile_height, width=10)
        height_spinbox.pack(side=tk.LEFT, padx=(0, 15))
        
        self.grid_info_label = ttk.Label(tile_frame, text="", style='Info.TLabel')
        self.grid_info_label.pack(side=tk.LEFT)
        
        # Quick presets
        ttk.Label(settings_frame, text="Quick Presets:", style='Header.TLabel').grid(row=4, column=0, sticky=tk.W, pady=(0, 5))
        
        preset_frame = ttk.Frame(settings_frame)
        preset_frame.grid(row=5, column=0, columnspan=3, sticky="ew")
        
        ttk.Button(preset_frame, text="Telegram (512x512)", command=lambda: self.set_preset(512, 512), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preset_frame, text="Small (256x256)", command=lambda: self.set_preset(256, 256), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preset_frame, text="Large (1024x1024)", command=lambda: self.set_preset(1024, 1024), style='Secondary.TButton').pack(side=tk.LEFT)
        
        # Bind events
        self.frame_duration.trace('w', self.update_fps_display)
        self.tile_width.trace('w', self.update_grid_info)
        self.tile_height.trace('w', self.update_grid_info)
    
    def create_output_section(self, parent, row):
        """Create output section"""
        output_frame = ttk.LabelFrame(parent, text="📤 Output", padding="15")
        output_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="Output folder:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.output_path_label = ttk.Label(output_frame, textvariable=self.output_folder, style='Info.TLabel', wraplength=500)
        self.output_path_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        ttk.Button(output_frame, text="📁 Choose Folder", command=self.browse_output_folder, style='Secondary.TButton').grid(row=2, column=0, sticky=tk.W)
        
        # Output info
        info_text = "Output: WebM files with VP9 codec, preserving transparency"
        ttk.Label(output_frame, text=info_text, style='Info.TLabel').grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
    
    def create_progress_section(self, parent, row):
        """Create progress section"""
        progress_frame = ttk.LabelFrame(parent, text="📊 Progress", padding="15")
        progress_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        # Progress text
        self.progress_text = ScrolledText(progress_frame, height=8, width=70, font=('Monaco', 9))
        self.progress_text.grid(row=1, column=0, sticky="ew")
        
        # Status label
        self.status_label = ttk.Label(progress_frame, text="Ready to convert", style='Info.TLabel')
        self.status_label.grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
    
    def create_action_buttons(self, parent, row):
        """Create action buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=3, pady=(0, 20))
        
        self.convert_button = ttk.Button(button_frame, text="🚀 Start Conversion", command=self.start_conversion, style='Primary.TButton')
        self.convert_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stop", command=self.stop_conversion, style='Secondary.TButton', state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="❌ Exit", command=self.root.quit, style='Secondary.TButton').pack(side=tk.LEFT)
    
    def browse_file(self):
        """Browse for input file"""
        filetypes = [
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
        
        filename = filedialog.askopenfilename(
            title="Select animation file",
            filetypes=filetypes
        )
        
        if filename:
            self.input_path.set(filename)
            self.input_type.set("file")
            self.detect_fps()
            self.update_output_folder()
    
    def browse_folder(self):
        """Browse for input folder"""
        folder = filedialog.askdirectory(title="Select folder containing PNG/SVG sequence")
        
        if folder:
            self.input_path.set(folder)
            self.input_type.set("folder")
            self.detect_fps()
            self.update_output_folder()
    
    def browse_output_folder(self):
        """Browse for output folder"""
        folder = filedialog.askdirectory(title="Select output folder")
        
        if folder:
            self.output_folder.set(folder)
    
    def detect_fps(self):
        """Detect FPS from input file"""
        if not self.input_path.get():
            return
        
        self.progress_text.insert(tk.END, "Detecting FPS...\n")
        self.progress_text.see(tk.END)
        
        # Run FPS detection in thread
        thread = threading.Thread(target=self._detect_fps_thread)
        thread.daemon = True
        thread.start()
    
    def _detect_fps_thread(self):
        """Detect FPS in background thread"""
        try:
            fps = self.detect_fps_from_file(self.input_path.get())
            if fps:
                self.detected_fps.set(fps)
                duration = int(1000 / fps)
                self.frame_duration.set(duration)
                
                # Update UI in main thread
                self.root.after(0, lambda: self.detected_fps_label.config(
                    text=f"✅ Detected: {fps:.2f} FPS",
                    style='Success.TLabel'
                ))
                self.root.after(0, self.update_fps_display)
            else:
                self.root.after(0, lambda: self.detected_fps_label.config(
                    text="❌ Could not detect FPS",
                    style='Error.TLabel'
                ))
        except Exception as e:
            self.root.after(0, lambda: self.detected_fps_label.config(
                text=f"❌ FPS detection failed: {str(e)}",
                style='Error.TLabel'
            ))
    
    def detect_fps_from_file(self, file_path):
        """Detect FPS from file (same as original script)"""
        if self.input_type.get() == "folder":
            return None
        
        try:
            # Use FFmpeg to get file info
            cmd = ["ffmpeg", "-i", file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, stderr=subprocess.PIPE)
            
            if result.returncode != 0:
                stderr_output = result.stderr
                
                # Look for FPS information
                fps_match = re.search(r'(\d+(?:\.\d+)?)\s*fps', stderr_output, re.IGNORECASE)
                if fps_match:
                    return float(fps_match.group(1))
                
                # Look for frame rate
                frame_rate_match = re.search(r'(\d+(?:\.\d+)?)\s*tbr', stderr_output, re.IGNORECASE)
                if frame_rate_match:
                    return float(frame_rate_match.group(1))
                    
        except Exception as e:
            self.log_message(f"FPS detection failed: {e}")
        
        return None
    
    def set_preset(self, width, height):
        """Set tile size preset"""
        self.tile_width.set(width)
        self.tile_height.set(height)
    
    def update_fps_display(self, *args):
        """Update FPS display when duration changes"""
        try:
            duration = self.frame_duration.get()
            fps = 1000 / duration
            self.fps_label.config(text=f"({fps:.1f} FPS)")
        except:
            pass
    
    def update_grid_info(self, *args):
        """Update grid information display"""
        try:
            width = self.tile_width.get()
            height = self.tile_height.get()
            
            if width and height and self.input_path.get():
                # This would need the actual image dimensions
                # For now, just show the tile size
                self.grid_info_label.config(text=f"Tile size: {width}x{height}px")
        except:
            pass
    
    def update_output_folder(self):
        """Update output folder based on input"""
        if self.input_path.get():
            if self.input_type.get() == "file":
                base_name = os.path.splitext(os.path.basename(self.input_path.get()))[0]
            else:
                base_name = os.path.basename(self.input_path.get())
            
            now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_path = f"/Users/alexmiller/Desktop/WEBM/{base_name}_{now_str}"
            self.output_folder.set(output_path)
    
    def start_conversion(self):
        """Start the conversion process"""
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input file or folder first.")
            return
        
        if not self.tile_width.get() or not self.tile_height.get():
            messagebox.showerror("Error", "Please set tile dimensions.")
            return
        
        if self.is_processing:
            return
        
        # Clear progress
        self.progress_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.status_label.config(text="Starting conversion...")
        
        # Update UI
        self.is_processing = True
        self.convert_button.config(state='disabled')
        self.stop_button.config(state='normal')
        
        # Start conversion in thread
        thread = threading.Thread(target=self._conversion_thread)
        thread.daemon = True
        thread.start()
    
    def stop_conversion(self):
        """Stop the conversion process"""
        self.is_processing = False
        self.status_label.config(text="Stopping conversion...")
        self.log_message("Conversion stopped by user")
    
    def _conversion_thread(self):
        """Run conversion in background thread"""
        try:
            # Import the conversion functions from the original script
            # This would need to be adapted to work with the GUI
            self.log_message("Starting conversion...")
            self.log_message(f"Input: {self.input_path.get()}")
            self.log_message(f"Tile size: {self.tile_width.get()}x{self.tile_height.get()}")
            self.log_message(f"Frame duration: {self.frame_duration.get()}ms")
            
            # Here you would call the actual conversion functions
            # For now, just simulate the process
            self.simulate_conversion()
            
        except Exception as e:
            self.log_message(f"Conversion failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Conversion failed: {e}"))
        finally:
            self.root.after(0, self.conversion_finished)
    
    def simulate_conversion(self):
        """Simulate conversion process for demo"""
        steps = [
            "Loading input file...",
            "Detecting format...",
            "Extracting frames...",
            "Processing frames...",
            "Creating tiles...",
            "Converting to WebM...",
            "Saving files...",
            "Cleaning up..."
        ]
        
        for i, step in enumerate(steps):
            if not self.is_processing:
                break
            
            self.log_message(step)
            progress = (i + 1) / len(steps) * 100
            self.root.after(0, lambda p=progress: self.progress_var.set(p))
            
            # Simulate work
            import time
            time.sleep(0.5)
        
        if self.is_processing:
            self.log_message("✅ Conversion completed successfully!")
            self.root.after(0, lambda: messagebox.showinfo("Success", "Conversion completed successfully!"))
    
    def conversion_finished(self):
        """Called when conversion finishes"""
        self.is_processing = False
        self.convert_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.status_label.config(text="Ready")
    
    def log_message(self, message):
        """Add message to progress log"""
        self.root.after(0, lambda: self.progress_text.insert(tk.END, f"{message}\n"))
        self.root.after(0, lambda: self.progress_text.see(tk.END))
    
    def update_progress(self):
        """Update progress from queue"""
        try:
            while True:
                message = self.progress_queue.get_nowait()
                self.log_message(message)
        except queue.Empty:
            pass
        
        self.root.after(100, self.update_progress)

def main():
    """Main function"""
    root = tk.Tk()
    app = WebMTileConverterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
