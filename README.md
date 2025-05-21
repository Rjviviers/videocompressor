# Media Converter Pro

This Python script provides a graphical user interface (GUI) to automate the conversion of an entire media library to MP4 H.265 (HEVC), optimizing for quality and streamability.

## Features

-   **User-Friendly GUI:** Easy selection of media directory and conversion options.
-   **Real-time Progress:**
    -   Overall progress bar.
    -   Lists of pending and processed files with their status (Converted, Skipped, Failed).
    -   Detailed log output within the GUI.
-   **Comprehensive Conversion Options:**
    -   Recursive conversion of video files in a directory.
    -   H.265 (HEVC) encoding using MP4 container, with Web Optimization (`+faststart`).
    -   GPU hardware acceleration support (NVIDIA NVENC, Intel QSV, AMD AMF) with CPU (libx265) fallback.
    -   Configurable H.265 quality level and profile (`main`, `main10`).
    -   Configurable audio codec (e.g., `aac`, `copy`) and quality.
    -   Automatic selection of English audio and text-based subtitle tracks.
-   **File Management:**
    -   Safe file replacement upon successful conversion and verification.
    -   Option to skip conversion if a target MP4 file already exists.
-   **Robustness:**
    -   Detailed file logging (`conversion_gui.log` by default).
    -   Dry-run mode to preview actions without modifying files.

## Prerequisites

1.  **Python 3.7 or newer:**
    The script uses features available in Python 3.7+.
    You can download Python from [python.org](https://www.python.org/).

2.  **FFmpeg and ffprobe:**
    These are essential for video and audio processing. The script expects `ffmpeg` and `ffprobe` to be installed and accessible in your system's PATH.
    -   **Windows:** Download from [FFmpeg official builds](https://ffmpeg.org/download.html#build-windows) (e.g., gyan.dev or BtbN builds) and add the `bin` directory (containing `ffmpeg.exe` and `ffprobe.exe`) to your system's PATH environment variable.
    -   **Linux (Ubuntu/Debian):** `sudo apt update && sudo apt install ffmpeg`
    -   **macOS (using Homebrew):** `brew install ffmpeg`

## Setup

1.  Clone this repository or download the script files (`main.py`, `conversion_utils.py`, `ffmpeg_wrapper.py`, `requirements.txt`).
2.  Ensure Python 3.7+ is installed.
3.  Ensure FFmpeg and ffprobe are installed and in your system PATH.

## Usage

Run the script using Python to launch the GUI:

```bash
python main.py
```

**Using the GUI:**

1.  **Media Directory:** Click "Browse" to select the root directory of your media library.
2.  **GPU Type:** Select your desired GPU for encoding from the dropdown (or `cpu` for software encoding).
3.  **Advanced Settings (Optional):**
    *   **Quality Level:** Set the video quality (e.g., `23`).
    *   **H.265 Profile:** Choose `main` or `main10`.
    *   **Audio Codec:** Specify the audio codec (e.g., `aac`, `copy`).
    *   **Audio Quality:** Set audio quality (ignored if codec is `copy`).
    *   **Skip if .mp4 Exists:** Check to avoid re-converting if a target MP4 already exists.
    *   **Dry Run:** Check to simulate the conversion process, logging actions without making changes.
4.  **Start Conversion:** Click the "Start Conversion" button.

**Monitoring Progress:**

-   The **Pending Files** list shows videos queued for conversion.
-   The **Processed Files** list updates with the status of each completed file.
-   The **Progress Bar** shows overall completion.
-   The **Log** area displays detailed messages from the conversion process.

**(Optional) Command-line Overrides for Defaults:**
While the GUI is the primary interface, initial default values for some settings can still be influenced by command-line arguments if you choose to run the script with them (e.g., `python main.py --gpu_type cpu`). However, settings chosen in the GUI will take precedence for the actual conversion task started from the GUI.

## Script Structure

-   `main.py`: Main execution script, Tkinter GUI, argument parsing for defaults, logging setup.
-   `conversion_utils.py`: Directory traversal, file orchestration, resumability logic, GUI update messaging.
-   `ffmpeg_wrapper.py`: FFmpeg/ffprobe interaction, command construction, file conversion, verification.
-   `requirements.txt`: Notes on dependencies.

## Logging

-   GUI: Logs are displayed in the "Log" text area.
-   File: Detailed logs are also written to `conversion_gui.log` (or the file specified by the `--log_file` CLI argument if used) in the script's directory. Log files are rotated (5 files, 5MB each).

## Contributing

Feel free to open issues or submit pull requests if you find bugs or have suggestions for improvements. 