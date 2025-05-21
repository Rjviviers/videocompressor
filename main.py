import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
import threading
import queue

# Configure logging (Best practice: from a config file or more detailed setup)
# Basic setup for demonstration:
# logging.basicConfig(
# level=logging.INFO,
# format='%(asctime)s - %(levelname)s - %(message)s',
# handlers= # This line caused the error
# )
# For long running scripts, consider RotatingFileHandler or TimedRotatingFileHandler [33]

def setup_logging(log_file, log_level_str):
    """Configures logging to file and console."""
    numeric_level = getattr(logging, log_level_str.upper(), None)
    if not isinstance(numeric_level, int):
        # Fallback for GUI if logger not fully set up by CLI args parsing
        print(f"Warning: Invalid log level: {log_level_str}. Defaulting to INFO.")
        numeric_level = logging.INFO
        log_level_str = "INFO" # ensure consistency

    # Create a logger
    logger = logging.getLogger()
    
    # Clear existing handlers if any (e.g., if called multiple times)
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(numeric_level)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s')

    # File Handler (ensure log_file path is valid)
    try:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        fh = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=5)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except Exception as e:
        print(f"Error setting up file logger for {log_file}: {e}. Logging to console only.")

    # Console Handler (for GUI, we might redirect this to the text widget)
    # For now, let it also log to actual console for debugging GUI itself
    ch_console = logging.StreamHandler(sys.stdout) 
    ch_console.setFormatter(formatter)
    ch_console.setLevel(numeric_level) # Respect log level for console too
    logger.addHandler(ch_console)
    
    logging.info(f"Logging initialized (level: {log_level_str}, file: {log_file}).")


def setup_argument_parser():
    parser = argparse.ArgumentParser(description="Convert media library to MP4 H.265.")
    parser.add_argument("-i", "--input_dir", help="Root directory of the media library on the NAS.")
    parser.add_argument("-g", "--gpu_type", choices=['nvidia', 'intel', 'amd', 'cpu'], default='nvidia', help="GPU to use for encoding ('cpu' for libx265).")
    parser.add_argument("--quality_level", type=int, default=23, help="Quality target (e.g., CRF 23 for libx265, CQ 23 for NVENC).")
    parser.add_argument("--h265_profile", choices=['main', 'main10'], default='main', help="H.265 profile.")
    parser.add_argument("--audio_codec", default='aac', help="Target audio codec (e.g., 'aac', or 'copy').")
    parser.add_argument("--audio_quality", default='2', help="Quality for AAC (e.g., VBR qscale:a 2). Ignored if audio_codec is 'copy'.")
    parser.add_argument("--skip_existing", action='store_true', default=False, help="Skip conversion if an MP4 with the same base name already exists.")
    parser.add_argument("--log_file", default='conversion_gui.log', help="Path for the log file.")
    parser.add_argument("--log_level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help="Logging level.")
    parser.add_argument("--dry_run", action='store_true', default=False, help="Log actions but do not execute FFmpeg or modify files.")
    return parser

class Application(tk.Tk):
    def __init__(self, args):
        super().__init__()
        self.args = args # Store default/CLI args
        self.title("Media Converter Pro")
        self.geometry("900x750") # Increased size for lists

        self.update_queue = queue.Queue()
        self.current_pending_files = [] # To manage the pending listbox items

        # Main layout frames
        top_controls_frame = ttk.Frame(self)
        top_controls_frame.pack(padx=10, pady=5, fill="x")

        lists_frame = ttk.Frame(self)
        lists_frame.pack(padx=10, pady=5, fill="both", expand=True)

        progress_and_log_frame = ttk.Frame(self)
        progress_and_log_frame.pack(padx=10, pady=5, fill="x")

        # --- Input Options Frame (in top_controls_frame) ---
        input_options_frame = ttk.LabelFrame(top_controls_frame, text="Input & GPU", padding=(10, 5))
        input_options_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nswe")
        ttk.Label(input_options_frame, text="Media Directory:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.input_dir_var = tk.StringVar(value=self.args.input_dir or "")
        self.input_dir_entry = ttk.Entry(input_options_frame, textvariable=self.input_dir_var, width=40)
        self.input_dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.browse_button = ttk.Button(input_options_frame, text="Browse", command=self.browse_directory)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)
        
        ttk.Label(input_options_frame, text="GPU Type:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.gpu_type_var = tk.StringVar(value=self.args.gpu_type)
        self.gpu_type_combo = ttk.Combobox(input_options_frame, textvariable=self.gpu_type_var, values=['nvidia', 'intel', 'amd', 'cpu'], state="readonly", width=10)
        self.gpu_type_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        input_options_frame.columnconfigure(1, weight=1)

        # --- Advanced Options Frame (in top_controls_frame) ---
        adv_options_frame = ttk.LabelFrame(top_controls_frame, text="Advanced Settings", padding=(10, 5))
        adv_options_frame.grid(row=0, column=1, padx=5, pady=5, sticky="nswe")
        ttk.Label(adv_options_frame, text="Quality Level:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.quality_level_var = tk.IntVar(value=self.args.quality_level)
        self.quality_level_entry = ttk.Entry(adv_options_frame, textvariable=self.quality_level_var, width=7)
        self.quality_level_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(adv_options_frame, text="H.265 Profile:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.h265_profile_var = tk.StringVar(value=self.args.h265_profile)
        self.h265_profile_combo = ttk.Combobox(adv_options_frame, textvariable=self.h265_profile_var, values=['main', 'main10'], state="readonly", width=7)
        self.h265_profile_combo.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(adv_options_frame, text="Audio Codec:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.audio_codec_var = tk.StringVar(value=self.args.audio_codec)
        self.audio_codec_entry = ttk.Entry(adv_options_frame, textvariable=self.audio_codec_var, width=7)
        self.audio_codec_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.audio_codec_var.trace_add("write", self.toggle_audio_quality_entry)

        ttk.Label(adv_options_frame, text="Audio Quality:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.audio_quality_var = tk.StringVar(value=self.args.audio_quality)
        self.audio_quality_entry = ttk.Entry(adv_options_frame, textvariable=self.audio_quality_var, width=7)
        self.audio_quality_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        self.toggle_audio_quality_entry()
        self.skip_existing_var = tk.BooleanVar(value=self.args.skip_existing)
        self.skip_existing_check = ttk.Checkbutton(adv_options_frame, text="Skip .mp4 Exists", variable=self.skip_existing_var)
        self.skip_existing_check.grid(row=2, column=0, padx=5, pady=10, sticky="w")
        self.dry_run_var = tk.BooleanVar(value=self.args.dry_run)
        self.dry_run_check = ttk.Checkbutton(adv_options_frame, text="Dry Run", variable=self.dry_run_var)
        self.dry_run_check.grid(row=2, column=1, columnspan=2, padx=5, pady=10, sticky="w")
        top_controls_frame.columnconfigure(0, weight=1)
        top_controls_frame.columnconfigure(1, weight=1)

        # --- Pending Files Listbox (in lists_frame) ---
        pending_frame = ttk.LabelFrame(lists_frame, text="Pending Files", padding=(10,5))
        pending_frame.pack(side="left", padx=5, pady=5, fill="both", expand=True)
        self.pending_listbox = tk.Listbox(pending_frame, height=10)
        self.pending_listbox.pack(side="left", fill="both", expand=True)
        pending_scrollbar = ttk.Scrollbar(pending_frame, orient="vertical", command=self.pending_listbox.yview)
        pending_scrollbar.pack(side="right", fill="y")
        self.pending_listbox.config(yscrollcommand=pending_scrollbar.set)

        # --- Processed Files Listbox (in lists_frame) ---
        processed_frame = ttk.LabelFrame(lists_frame, text="Processed Files", padding=(10,5))
        processed_frame.pack(side="right", padx=5, pady=5, fill="both", expand=True)
        self.processed_listbox = tk.Listbox(processed_frame, height=10)
        self.processed_listbox.pack(side="left", fill="both", expand=True)
        processed_scrollbar = ttk.Scrollbar(processed_frame, orient="vertical", command=self.processed_listbox.yview)
        processed_scrollbar.pack(side="right", fill="y")
        self.processed_listbox.config(yscrollcommand=processed_scrollbar.set)
        
        # --- Controls Frame (Start Button) ---
        control_frame = ttk.Frame(progress_and_log_frame, padding=(0,0)) # Reduced padding
        control_frame.pack(padx=0, pady=0, fill="x") # Fill x, but placed before progress
        self.start_button = ttk.Button(control_frame, text="Start Conversion", command=self.start_conversion_thread)
        self.start_button.pack(side="left", padx=5, pady=5)
        
        # --- Progress Frame (in progress_and_log_frame) ---
        progress_frame = ttk.LabelFrame(progress_and_log_frame, text="Progress", padding=(10, 5))
        progress_frame.pack(padx=0, pady=5, fill="x") # Reduced padx
        self.progress_label_var = tk.StringVar(value="0/0 files | 0%")
        ttk.Label(progress_frame, textvariable=self.progress_label_var).pack(side="left", padx=5)
        self.progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(side="left", padx=5, fill="x", expand=True)
        
        # --- Log Area Frame (in progress_and_log_frame) ---
        log_frame = ttk.LabelFrame(progress_and_log_frame, text="Log", padding=(10, 5))
        log_frame.pack(padx=0, pady=5, fill="both", expand=True) # Reduced padx, allow expand for log
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=8, state="disabled")
        self.log_text.pack(fill="both", expand=True)
        
        gui_log_handler = TextHandler(self.log_text, self.update_queue)
        gui_log_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(gui_log_handler)
        logging.getLogger().setLevel(min(logging.getLogger().level, getattr(logging, self.args.log_level.upper(), logging.INFO)))

        self.conversion_thread = None
        self.after(100, self.process_queue)

    def toggle_audio_quality_entry(self, *args):
        if self.audio_codec_var.get().lower() == 'copy':
            self.audio_quality_entry.config(state="disabled")
        else:
            self.audio_quality_entry.config(state="normal")

    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.input_dir_var.get() or os.path.expanduser("~"))
        if directory:
            self.input_dir_var.set(directory)
            self.log_message(f"Selected directory: {directory}")

    def log_message(self, message, level=logging.INFO):
        # This method can be used to explicitly add messages to the GUI log
        # For general logging, rely on the TextHandler
        self.update_queue.put(("log", message))
        if level == logging.INFO:
             logging.info(message) # also send to file log via standard logger
        elif level == logging.ERROR:
             logging.error(message)
        # etc. for other levels if needed for direct calls

    def get_config_from_gui(self):
        try:
            quality_level = self.quality_level_var.get()
        except tk.TclError:
            messagebox.showerror("Input Error", "Invalid Quality Level. Please enter a number.")
            return None
        
        return {
            "input_dir": self.input_dir_var.get(),
            "gpu_type": self.gpu_type_var.get(),
            "quality_level": quality_level,
            "h265_profile": self.h265_profile_var.get(),
            "audio_codec": self.audio_codec_var.get(),
            "audio_quality": self.audio_quality_var.get(),
            "skip_existing": self.skip_existing_var.get(),
            "dry_run": self.dry_run_var.get(),
            "log_file": self.args.log_file, 
            "log_level": self.args.log_level,
            "update_queue": self.update_queue
        }

    def set_controls_state(self, state):
        """Enable or disable controls during conversion."""
        self.start_button.config(state=state)
        self.browse_button.config(state=state)
        self.input_dir_entry.config(state=state)
        self.gpu_type_combo.config(state=state)
        self.quality_level_entry.config(state=state)
        self.h265_profile_combo.config(state=state)
        self.audio_codec_entry.config(state=state)
        self.audio_quality_entry.config(state=("disabled" if self.audio_codec_var.get().lower() == 'copy' else state))
        self.skip_existing_check.config(state=state)
        self.dry_run_check.config(state=state)

    def start_conversion_thread(self):
        current_config = self.get_config_from_gui()
        if not current_config:
            return

        if not current_config["input_dir"] or not os.path.isdir(current_config["input_dir"]):
            self.log_message("Error: Please select a valid input directory.", logging.ERROR)
            messagebox.showerror("Error", "Please select a valid input directory.")
            return

        self.set_controls_state("disabled")
        self.progress_bar["value"] = 0
        self.progress_label_var.set("Scanning... | 0%")
        self.log_message(f"Starting conversion for: {current_config['input_dir']}", logging.INFO)
        logging.info(f"Conversion settings: {current_config}") # Log the full config
        
        # Clear previous lists
        self.pending_listbox.delete(0, tk.END)
        self.processed_listbox.delete(0, tk.END)
        self.current_pending_files.clear()
        
        from conversion_utils import process_media_library
        self.conversion_thread = threading.Thread(target=process_media_library, 
                                              args=(current_config["input_dir"], current_config),
                                              daemon=True)
        self.conversion_thread.start()

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.update_queue.get_nowait()
                if msg_type == "log":
                    self.log_text.config(state="normal")
                    self.log_text.insert(tk.END, data + "\n")
                    self.log_text.config(state="disabled")
                    self.log_text.see(tk.END)
                elif msg_type == "progress_max":
                    self.progress_bar["maximum"] = data
                elif msg_type == "progress_update":
                    current, total = data
                    self.progress_bar["value"] = current
                    percentage = (current / total * 100) if total > 0 else 0
                    self.progress_label_var.set(f"{current}/{total} files | {percentage:.1f}%")
                elif msg_type == "status_update":
                    # This can be used for more granular status, e.g. "Currently converting X..."
                    # For now, main logging handles file names.
                    pass 
                elif msg_type == "pending_files_list":
                    self.pending_listbox.delete(0, tk.END)
                    self.current_pending_files = [os.path.basename(f) for f in data] # Store basenames
                    for item in self.current_pending_files:
                        self.pending_listbox.insert(tk.END, item)
                elif msg_type == "file_processing_start": # data is full filepath
                    # Remove from pending listbox - match by basename
                    filename_to_remove = os.path.basename(data)
                    if filename_to_remove in self.current_pending_files:
                        try:
                            idx = self.current_pending_files.index(filename_to_remove)
                            self.pending_listbox.delete(idx)
                            self.current_pending_files.pop(idx)
                        except ValueError:
                            logging.warning(f"Could not find {filename_to_remove} in GUI pending list to remove.")
                elif msg_type == "file_processed_status": # data is (filepath, status_str)
                    filepath, status_str = data
                    base_filename = os.path.basename(filepath)
                    self.processed_listbox.insert(tk.END, f"[{status_str.upper()}] {base_filename}")
                    self.processed_listbox.see(tk.END)
                    # Ensure it's removed from pending if not already by file_processing_start
                    if base_filename in self.current_pending_files:
                         try:
                            idx = self.current_pending_files.index(base_filename)
                            self.pending_listbox.delete(idx)
                            self.current_pending_files.pop(idx)
                         except ValueError:
                            pass # Already removed or wasn't there, harmless
                elif msg_type == "conversion_complete":
                    self.log_message(f"Conversion finished. Summary: {data}", logging.INFO)
                    messagebox.showinfo("Complete", f"Conversion process finished.\n{data}")
                    self.set_controls_state("normal")
                    self.progress_label_var.set(f"Completed | {data}")

        except queue.Empty:
            pass
        finally:
            self.after(100, self.process_queue)

# Custom logging handler to redirect logs to the Tkinter Text widget
class TextHandler(logging.Handler):
    def __init__(self, text_widget, update_queue):
        super().__init__()
        self.text_widget = text_widget
        self.update_queue = update_queue

    def emit(self, record):
        msg = self.format(record)
        # Send log message to the main thread via queue to update GUI
        self.update_queue.put(("log", msg))

def main():
    # Use argparse to get default values and allow CLI overrides if someone runs
    # it with args, though GUI will be primary.
    parser = setup_argument_parser()
    args = parser.parse_args() # Parses CLI args, or uses defaults if none given
    
    # Setup file logging based on (potentially CLI overridden) args
    # Ensure log_file path is determined correctly before logger setup
    if not os.path.isabs(args.log_file) and hasattr(sys, '_MEIPASS'): # PyInstaller bundle
        args.log_file = os.path.join(os.path.dirname(sys.executable), args.log_file)
    elif not os.path.isabs(args.log_file):
        args.log_file = os.path.join(os.getcwd(), args.log_file)

    setup_logging(args.log_file, args.log_level)

    logging.info("Application starting with GUI.")
    logging.debug(f"Initial args/defaults: {args}")

    app = Application(args)
    app.mainloop()

if __name__ == "__main__":
    main()