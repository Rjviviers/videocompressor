# Media Library HEVC Converter

This Python script automates the conversion of an entire media library to MP4 H.265 (HEVC), optimizing for quality and streamability.

## Features

-   Recursive conversion of video files in a directory.
-   H.265 (HEVC) encoding using MP4 container.
-   GPU hardware acceleration support (NVIDIA NVENC, Intel QSV, AMD AMF) with CPU (libx265) fallback.
-   Automatic selection of English audio and text-based subtitle tracks.
-   Safe file replacement upon successful conversion and verification.
-   Resumable: skips already converted files.
-   Detailed logging and error handling.
-   Configurable encoding parameters (quality, profile, audio codec, etc.).
-   Dry-run mode to preview actions.

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

Run the script from your terminal:

```bash
python main.py --input_dir /path/to/your/media --gpu_type nvidia [other options]
```

### Command-line Arguments

-   `-i, --input_dir` (Required): Root directory of the media library.
-   `-g, --gpu_type`: GPU for encoding. Choices: `nvidia`, `intel`, `amd`, `cpu`. (Default: `nvidia`)
-   `--quality_level`: Quality target (e.g., CRF for libx265, CQ for NVENC). (Default: `23`)
-   `--h265_profile`: H.265 profile. Choices: `main`, `main10`. (Default: `main`)
-   `--audio_codec`: Target audio codec. (Default: `aac`; use `copy` to try stream copying)
-   `--audio_quality`: Quality for AAC audio. (Default: `2`)
-   `--skip_existing`: Skip conversion if an MP4 with the same base name already exists.
-   `--log_file`: Path for the log file. (Default: `conversion.log`)
-   `--log_level`: Logging level. Choices: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. (Default: `INFO`)
-   `--dry_run`: Log actions but do not execute FFmpeg or modify files.

### Examples

-   **Basic conversion using NVIDIA GPU:**
    ```bash
    python main.py -i "/mnt/mymedia" -g nvidia
    ```

-   **Convert with Intel QSV, Main10 profile, and skip existing MP4s:**
    ```bash
    python main.py -i "D:\Videos" -g intel --h265_profile main10 --skip_existing
    ```

-   **Dry run using CPU encoding, with detailed debug logging to a custom file:**
    ```bash
    python main.py -i "./media_folder" -g cpu --dry_run --log_level DEBUG --log_file "my_conversion_test.log"
    ```

## Script Structure

-   `main.py`: Main execution script, argument parsing, logging setup.
-   `conversion_utils.py`: Directory traversal, file orchestration, resumability logic.
-   `ffmpeg_wrapper.py`: FFmpeg/ffprobe interaction, command construction, file conversion, verification.

## Logging

Logs are written to `conversion.log` (or the file specified by `--log_file`) and also to the console.
Log files are rotated (5 files, 5MB each).

## Contributing

Feel free to open issues or submit pull requests if you find bugs or have suggestions for improvements. 