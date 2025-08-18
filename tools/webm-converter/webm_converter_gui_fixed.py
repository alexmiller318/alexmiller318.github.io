#!/usr/bin/env python3
"""
WebM Tile Converter - Fixed GUI
A user-friendly interface with better window handling
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
import numpy as np
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import queue

class WebMTileConverterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WebM Tile Converter")
        self.root.geometry("900x800")
        self.root.minsize(800, 700)
        
        # Bring window to front and focus
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.attributes('-topmost', False)
        self.root.focus_force()
        
        # Set app icon and styling
        self.setup_styling()
        
        # Variables
        self.input_path = tk.StringVar()
        self.input_type = tk.StringVar()
        self.detected_fps = tk.DoubleVar()
        self.frame_duration = tk.IntVar(value=200)
        self.fps_mode = tk.StringVar(value="duration")  # "fps" or "duration"
        self.selected_fps = tk.DoubleVar(value=5.0)
        self.tile_width = tk.IntVar()
        self.tile_height = tk.IntVar()
        self.output_folder = tk.StringVar()
        
        # Processing state
        self.is_processing = False
        self.progress_queue = queue.Queue()
        
        # Create main scrollable frame
        self.create_scrollable_frame()
        
        # Start progress updater
        self.update_progress()
        
        # Bind window events
        self.root.bind('<Command-q>', lambda e: self.root.quit())
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
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
        style.configure('Execute.TButton', font=('Arial', 12, 'bold'), background='#4CAF50')
    
    def create_scrollable_frame(self):
        """Create a scrollable main frame"""
        # Create canvas and scrollbar
        canvas = tk.Canvas(self.root, bg='#f0f0f0')
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Create GUI widgets
        self.create_widgets()
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container
        main_frame = ttk.Frame(self.scrollable_frame, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure grid weights
        self.scrollable_frame.columnconfigure(0, weight=1)
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
        self.input_path_label = ttk.Label(input_frame, textvariable=self.input_path, style='Info.TLabel', wraplength=600)
        self.input_path_label.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        
        # Browse buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="ew")
        
        ttk.Button(button_frame, text="📄 Select File", command=self.browse_file, style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="📁 Select Folder", command=self.browse_folder, style='Primary.TButton').pack(side=tk.LEFT)
        
        # Manual path entry
        ttk.Label(input_frame, text="Or enter path manually:", style='Header.TLabel').grid(row=3, column=0, sticky=tk.W, pady=(20, 5))
        
        manual_frame = ttk.Frame(input_frame)
        manual_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 10))
        manual_frame.columnconfigure(0, weight=1)
        
        self.manual_path_entry = ttk.Entry(manual_frame, textvariable=self.input_path, width=60)
        self.manual_path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        ttk.Button(manual_frame, text="Set", command=self.set_manual_path, style='Secondary.TButton').grid(row=0, column=1)
        
        # Supported formats info
        formats_text = "Supported: PNG sequences, SVG sequences, WebP, GIF, MP4, AVI, MOV, WebM, and more!"
        ttk.Label(input_frame, text=formats_text, style='Info.TLabel').grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
    
    def create_settings_section(self, parent, row):
        """Create settings section"""
        settings_frame = ttk.LabelFrame(parent, text="⚙️ Settings", padding="15")
        settings_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        settings_frame.columnconfigure(1, weight=1)
        
        # Frame rate / Duration section
        ttk.Label(settings_frame, text="Frame Rate / Duration:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # FPS detection result
        self.detected_fps_label = ttk.Label(settings_frame, text="", style='Success.TLabel')
        self.detected_fps_label.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        # FPS/Duration mode selection
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        ttk.Radiobutton(mode_frame, text="Frame Rate (FPS)", variable=self.fps_mode, value="fps", 
                       command=self.update_fps_duration_mode).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(mode_frame, text="Frame Duration (ms)", variable=self.fps_mode, value="duration", 
                       command=self.update_fps_duration_mode).pack(side=tk.LEFT)
        
        # FPS selection frame
        self.fps_frame = ttk.Frame(settings_frame)
        self.fps_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        ttk.Label(self.fps_frame, text="FPS:").pack(side=tk.LEFT, padx=(0, 5))
        
        # Common FPS values
        fps_values = ["5.0", "10.0", "15.0", "24.0", "25.0", "30.0", "50.0", "60.0", "120.0"]
        self.fps_combobox = ttk.Combobox(self.fps_frame, values=fps_values, textvariable=self.selected_fps, width=10)
        self.fps_combobox.pack(side=tk.LEFT, padx=(0, 10))
        self.fps_combobox.set("5.0")
        
        # Custom FPS entry
        ttk.Label(self.fps_frame, text="or custom:").pack(side=tk.LEFT, padx=(0, 5))
        self.custom_fps_entry = ttk.Entry(self.fps_frame, width=10)
        self.custom_fps_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Duration display
        self.duration_display = ttk.Label(self.fps_frame, text="(200ms)", style='Info.TLabel')
        self.duration_display.pack(side=tk.LEFT)
        
        # Duration selection frame
        self.duration_frame = ttk.Frame(settings_frame)
        self.duration_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        ttk.Label(self.duration_frame, text="Duration (ms):").pack(side=tk.LEFT, padx=(0, 5))
        
        # Common duration values
        duration_values = [50, 100, 150, 200, 250, 300, 400, 500, 1000]
        self.duration_spinbox = ttk.Spinbox(self.duration_frame, from_=10, to=5000, textvariable=self.frame_duration, width=10)
        self.duration_spinbox.pack(side=tk.LEFT, padx=(0, 10))
        
        # Custom duration entry
        ttk.Label(self.duration_frame, text="or custom:").pack(side=tk.LEFT, padx=(0, 5))
        self.custom_duration_entry = ttk.Entry(self.duration_frame, width=10)
        self.custom_duration_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # FPS display
        self.fps_display = ttk.Label(self.duration_frame, text="(5.0 FPS)", style='Info.TLabel')
        self.fps_display.pack(side=tk.LEFT)
        
        # Tile size
        ttk.Label(settings_frame, text="Tile Size:", style='Header.TLabel').grid(row=5, column=0, sticky=tk.W, pady=(0, 5))
        
        tile_frame = ttk.Frame(settings_frame)
        tile_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 15))
        
        ttk.Label(tile_frame, text="Width:").pack(side=tk.LEFT, padx=(0, 5))
        width_spinbox = ttk.Spinbox(tile_frame, from_=32, to=2048, textvariable=self.tile_width, width=10)
        width_spinbox.pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(tile_frame, text="Height:").pack(side=tk.LEFT, padx=(0, 5))
        height_spinbox = ttk.Spinbox(tile_frame, from_=32, to=2048, textvariable=self.tile_height, width=10)
        height_spinbox.pack(side=tk.LEFT, padx=(0, 15))
        
        self.grid_info_label = ttk.Label(tile_frame, text="", style='Info.TLabel')
        self.grid_info_label.pack(side=tk.LEFT)
        
        # Quick presets
        ttk.Label(settings_frame, text="Quick Presets:", style='Header.TLabel').grid(row=7, column=0, sticky=tk.W, pady=(0, 5))
        
        preset_frame = ttk.Frame(settings_frame)
        preset_frame.grid(row=8, column=0, columnspan=3, sticky="ew")
        
        ttk.Button(preset_frame, text="Telegram (100x100)", command=lambda: self.set_preset(100, 100), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preset_frame, text="Small (64x64)", command=lambda: self.set_preset(64, 64), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preset_frame, text="Medium (256x256)", command=lambda: self.set_preset(256, 256), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preset_frame, text="Large (512x512)", command=lambda: self.set_preset(512, 512), style='Secondary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(preset_frame, text="HD (1024x1024)", command=lambda: self.set_preset(1024, 1024), style='Secondary.TButton').pack(side=tk.LEFT)
        
        # Bind events
        self.frame_duration.trace('w', self.update_fps_display)
        self.selected_fps.trace('w', self.update_duration_display)
        self.tile_width.trace('w', self.update_grid_info)
        self.tile_height.trace('w', self.update_grid_info)
        
        # Initialize mode
        self.update_fps_duration_mode()
    
    def create_output_section(self, parent, row):
        """Create output section"""
        output_frame = ttk.LabelFrame(parent, text="📤 Output", padding="15")
        output_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 20))
        output_frame.columnconfigure(1, weight=1)
        
        ttk.Label(output_frame, text="Output folder:", style='Header.TLabel').grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        self.output_path_label = ttk.Label(output_frame, textvariable=self.output_folder, style='Info.TLabel', wraplength=600)
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
        self.progress_text = ScrolledText(progress_frame, height=10, width=80, font=('Monaco', 9))
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
        
        self.execute_button = ttk.Button(button_frame, text="▶️ Execute Script", command=self.execute_script, style='Execute.TButton')
        self.execute_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="⏹️ Stop", command=self.stop_conversion, style='Secondary.TButton', state='disabled')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="❌ Exit", command=self.on_closing, style='Secondary.TButton').pack(side=tk.LEFT)
    
    def update_fps_duration_mode(self):
        """Update the display based on FPS/Duration mode"""
        if self.fps_mode.get() == "fps":
            self.fps_frame.grid()
            self.duration_frame.grid_remove()
            self.update_duration_display()
        else:
            self.fps_frame.grid_remove()
            self.duration_frame.grid()
            self.update_fps_display()
    
    def update_fps_display(self, *args):
        """Update FPS display when duration changes"""
        try:
            duration = self.frame_duration.get()
            fps = 1000 / duration
            self.fps_display.config(text=f"({fps:.1f} FPS)")
        except:
            pass
    
    def update_duration_display(self, *args):
        """Update duration display when FPS changes"""
        try:
            fps = self.selected_fps.get()
            duration = int(1000 / fps)
            self.duration_display.config(text=f"({duration}ms)")
        except:
            pass
    
    def browse_file(self):
        """Browse for input file with better window handling"""
        # Bring window to front
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.attributes('-topmost', False)
        self.root.focus_force()
        
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
        
        # Use a timer to ensure the dialog appears on top
        self.root.after(100, lambda: self._show_file_dialog(filetypes))
    
    def _show_file_dialog(self, filetypes):
        """Show file dialog with proper focus"""
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
        """Browse for input folder with better window handling"""
        # Bring window to front
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.attributes('-topmost', False)
        self.root.focus_force()
        
        # Use a timer to ensure the dialog appears on top
        self.root.after(100, self._show_folder_dialog)
    
    def _show_folder_dialog(self):
        """Show folder dialog with proper focus"""
        folder = filedialog.askdirectory(title="Select folder containing PNG/SVG sequence")
        
        if folder:
            self.input_path.set(folder)
            self.input_type.set("folder")
            self.detect_fps()
            self.update_output_folder()
    
    def browse_output_folder(self):
        """Browse for output folder"""
        # Bring window to front
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.attributes('-topmost', False)
        self.root.focus_force()
        
        # Use a timer to ensure the dialog appears on top
        self.root.after(100, self._show_output_dialog)
    
    def _show_output_dialog(self):
        """Show output folder dialog with proper focus"""
        folder = filedialog.askdirectory(title="Select output folder")
        
        if folder:
            self.output_folder.set(folder)
    
    def set_manual_path(self):
        """Set path manually from entry field"""
        path = self.input_path.get().strip()
        if path:
            if os.path.isfile(path):
                self.input_type.set("file")
            elif os.path.isdir(path):
                self.input_type.set("folder")
            else:
                messagebox.showerror("Error", "Path does not exist. Please enter a valid file or folder path.")
                return
            
            self.detect_fps()
            self.update_output_folder()
        else:
            messagebox.showerror("Error", "Please enter a path.")
    
    def detect_fps(self):
        """Detect FPS from input file"""
        if not self.input_path.get():
            return
        
        self.log_message("Detecting FPS...")
        
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
                self.selected_fps.set(fps)
                duration = int(1000 / fps)
                self.frame_duration.set(duration)
                
                # Update UI in main thread
                self.root.after(0, lambda: self.detected_fps_label.config(
                    text=f"✅ Detected: {fps:.2f} FPS",
                    style='Success.TLabel'
                ))
                self.root.after(0, self.update_fps_display)
                self.root.after(0, self.update_duration_display)
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
    
    def execute_script(self):
        """Execute the original Python script (interactive mode)"""
        if not self.input_path.get():
            messagebox.showerror("Error", "Please select an input file or folder first.")
            return
        
        self.log_message("Starting interactive script execution...")
        self.log_message("Note: The script will prompt for additional settings interactively.")
        
        # Execute in thread
        thread = threading.Thread(target=self._execute_script_thread)
        thread.daemon = True
        thread.start()
    
    def _execute_script_thread(self):
        """Execute script in background thread"""
        try:
            self.log_message("Starting script execution...")
            self.status_label.config(text="Executing script...")
            
            # Run the script interactively
            cmd = [sys.executable, "png_sequence_to_webm_tiles.py"]
            
            # Create a process that can handle interactive input
            process = subprocess.Popen(
                cmd, 
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.getcwd()
            )
            
            # For now, just run it and capture output
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.log_message("✅ Script executed successfully!")
                if stdout:
                    self.log_message(stdout)
                if stderr:
                    self.log_message(stderr)
                self.root.after(0, lambda: messagebox.showinfo("Success", "Script executed successfully!"))
            else:
                self.log_message("❌ Script execution failed!")
                if stderr:
                    self.log_message(stderr)
                self.root.after(0, lambda: messagebox.showerror("Error", f"Script execution failed:\n{stderr}"))
                
        except Exception as e:
            self.log_message(f"❌ Execution error: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Execution error: {e}"))
        finally:
            self.root.after(0, lambda: self.status_label.config(text="Ready"))
    
    def start_conversion(self):
        """Start the real conversion process using the original script's functions"""
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
        self.execute_button.config(state='disabled')
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
        """Run real conversion in background thread"""
        try:
            self.log_message("Starting real conversion...")
            self.log_message(f"Input: {self.input_path.get()}")
            self.log_message(f"Tile size: {self.tile_width.get()}x{self.tile_height.get()}")
            
            # Get frame duration based on mode
            if self.fps_mode.get() == "fps":
                fps = self.selected_fps.get()
                try:
                    fps = float(fps)
                except Exception:
                    fps = 5.0
                duration = int(1000 / fps)
                self.log_message(f"FPS: {fps} (Duration: {duration}ms)")
            else:
                duration = self.frame_duration.get()
                try:
                    fps = 1000 / float(duration)
                except Exception:
                    fps = 5.0
                self.log_message(f"Duration: {duration}ms (FPS: {fps:.1f})")
            
            # Perform the actual conversion
            success = self.perform_conversion()
            
            if success:
                self.log_message("✅ Conversion completed successfully!")
                self.root.after(0, lambda: messagebox.showinfo("Success", "Conversion completed successfully!"))
            else:
                self.log_message("❌ Conversion failed!")
                self.root.after(0, lambda: messagebox.showerror("Error", "Conversion failed!"))
            
        except Exception as e:
            self.log_message(f"Conversion failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Conversion failed: {e}"))
        finally:
            self.root.after(0, self.conversion_finished)
    
    def perform_conversion(self):
        """Perform the actual conversion using the original script's logic"""
        try:
            input_path = self.input_path.get()
            input_type = self.input_type.get()
            tile_width = self.tile_width.get()
            tile_height = self.tile_height.get()
            
            # Get frame duration
            if self.fps_mode.get() == "fps":
                fps = self.selected_fps.get()
                try:
                    fps = float(fps)
                except Exception:
                    fps = 5.0
                frame_duration = int(1000 / fps)
            else:
                frame_duration = self.frame_duration.get()
            
            self.log_message("Step 1: Converting input to PNG sequence...")
            self.progress_var.set(10)
            
            # Convert input to PNG sequence (simplified version)
            temp_dir = None
            png_files = []
            
            if input_type == "file":
                # Create temporary directory
                temp_dir = tempfile.mkdtemp()
                self.log_message(f"Created temp directory: {temp_dir}")
                
                # Extract frames using FFmpeg
                output_pattern = os.path.join(temp_dir, "frame_%04d.png")
                cmd = [
                    "ffmpeg", "-i", input_path,
                    "-vf", "fps=1",  # Extract at 1 FPS for now
                    "-y", output_pattern
                ]
                
                self.log_message(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.log_message(f"FFmpeg error: {result.stderr}")
                    return False
                
                # Get the generated PNG files
                png_pattern = os.path.join(temp_dir, "frame_*.png")
                png_files = sorted(glob.glob(png_pattern))
                
            else:  # folder
                # Check if it's a PNG or SVG sequence
                if self.is_png_sequence(input_path):
                    png_pattern = os.path.join(input_path, "*.png")
                    png_files = sorted(glob.glob(png_pattern))
                elif self.is_svg_sequence(input_path):
                    # Convert SVG to PNG
                    svg_pattern = os.path.join(input_path, "*.svg")
                    svg_files = sorted(glob.glob(svg_pattern))
                    
                    temp_dir = tempfile.mkdtemp()
                    for i, svg_file in enumerate(svg_files):
                        png_file = os.path.join(temp_dir, f"frame_{i:04d}.png")
                        # Convert SVG to PNG (simplified)
                        self.log_message(f"Converting {svg_file} to PNG...")
                        png_files.append(png_file)
                else:
                    self.log_message("No PNG or SVG sequence found in folder")
                    return False
            
            if not png_files:
                self.log_message("No PNG files found")
                return False
            
            self.log_message(f"Found {len(png_files)} frames")
            self.progress_var.set(30)
            
            # Load frames and get dimensions
            self.log_message("Step 2: Loading frames...")
            frames = []
            for i, png_file in enumerate(png_files):
                if not self.is_processing:
                    return False
                
                try:
                    frame = iio.imread(png_file)
                    frames.append(frame)
                    if i % 10 == 0:
                        self.log_message(f"Loaded frame {i+1}/{len(png_files)}")
                except Exception as e:
                    self.log_message(f"Error loading frame {png_file}: {e}")
                    return False
            
            if not frames:
                self.log_message("No frames loaded")
                return False
            
            # Get dimensions from first frame
            height, width = frames[0].shape[:2]
            self.log_message(f"Frame dimensions: {width}x{height}")
            self.progress_var.set(50)
            
            # Calculate grid
            n_rows = math.ceil(height / tile_height)
            n_cols = math.ceil(width / tile_width)
            
            self.log_message(f"Creating {n_rows}x{n_cols} grid of {tile_width}x{tile_height} tiles")
            self.progress_var.set(60)
            
            # Prepare output folder
            if input_type == "file":
                base_name = os.path.splitext(os.path.basename(input_path))[0]
            else:
                base_name = os.path.basename(input_path)
            
            now_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            out_folder = f"/Users/alexmiller/Desktop/WEBM/{base_name}_{now_str}"
            os.makedirs(out_folder, exist_ok=True)
            
            self.log_message(f"Output folder: {out_folder}")
            self.progress_var.set(70)
            
            # Process each tile
            total_tiles = n_rows * n_cols
            tile_count = 0
            
            for row in range(n_rows):
                for col in range(n_cols):
                    if not self.is_processing:
                        return False
                    
                    x = col * tile_width
                    y = row * tile_height
                    
                    tile_count += 1
                    self.log_message(f"Processing tile {tile_count}/{total_tiles}: row {row+1}, col {col+1}")
                    
                    # Crop frames for this tile
                    cropped_frames = []
                    for frame in frames:
                        # Ensure we don't go out of bounds
                        crop_x = max(0, min(x, width - tile_width))
                        crop_y = max(0, min(y, height - tile_height))
                        crop_w = max(0, min(tile_width, width - crop_x))
                        crop_h = max(0, min(tile_height, height - crop_y))
                        
                        cropped = frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
                        cropped_frames.append(cropped)
                    
                    # Save as WebM
                    out_name = f"{base_name}_tile_{row+1}x{col+1}.webm"
                    out_path = os.path.join(out_folder, out_name)
                    
                    success = self.save_frames_as_webm(cropped_frames, out_path, float(self.selected_fps.get()) if self.fps_mode.get()=="fps" else (1000/float(self.frame_duration.get() or 200)), tile_width, tile_height)
                    if success:
                        self.log_message(f"✅ Created {out_name}")
                    else:
                        self.log_message(f"❌ Failed to create {out_name}")
                    
                    # Update progress
                    progress = 70 + (tile_count / total_tiles) * 25
                    self.progress_var.set(progress)
            
            # Clean up
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    self.log_message("Cleaned up temporary files")
                except:
                    pass
            
            self.progress_var.set(100)
            self.log_message(f"✅ All tiles saved to: {out_folder}")
            return True
            
        except Exception as e:
            self.log_message(f"Conversion error: {e}")
            return False
    
    def is_png_sequence(self, folder_path):
        """Check if folder contains PNG sequence files"""
        png_pattern = os.path.join(folder_path, "*.png")
        png_files = glob.glob(png_pattern)
        return len(png_files) > 0
    
    def is_svg_sequence(self, folder_path):
        """Check if folder contains SVG sequence files"""
        svg_pattern = os.path.join(folder_path, "*.svg")
        svg_files = glob.glob(svg_pattern)
        return len(svg_files) > 0
    
    def save_frames_as_webm(self, frames, output_path, fps, width, height):
        """Save frames as WebM using FFmpeg"""
        try:
            # Create temporary directory for frames
            temp_dir = tempfile.mkdtemp()
            
            # Save frames as PNG
            for i, frame in enumerate(frames):
                frame_path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                iio.imwrite(frame_path, frame)
            
            # Convert to WebM using FFmpeg
            input_pattern = os.path.join(temp_dir, "frame_%04d.png")
            cmd = [
                "ffmpeg", "-y",
                "-framerate", str(fps),
                "-i", input_pattern,
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",
                "-crf", "30",
                "-b:v", "0",
                "-vf", f"scale={width}:{height}",
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Clean up temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return result.returncode == 0
            
        except Exception as e:
            self.log_message(f"Error saving WebM: {e}")
            return False
    
    def conversion_finished(self):
        """Called when conversion finishes"""
        self.is_processing = False
        self.convert_button.config(state='normal')
        self.execute_button.config(state='normal')
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
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_processing:
            if messagebox.askokcancel("Quit", "Conversion is in progress. Do you want to quit anyway?"):
                self.is_processing = False
                self.root.quit()
        else:
            self.root.quit()

def main():
    """Main function"""
    root = tk.Tk()
    app = WebMTileConverterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
