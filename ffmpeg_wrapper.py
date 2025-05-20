import subprocess
import json
import os
import logging

def get_stream_info(filepath):
    """Runs ffprobe and returns parsed JSON stream information."""
    cmd = [
        'ffprobe',
        '-v', 'quiet',
        '-print_format', 'json',
        '-show_format',
        '-show_streams',
        filepath
    ]
    logging.debug(f"Executing ffprobe command: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding='utf-8', errors='replace')
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        logging.error(f"ffprobe failed for {filepath}. Return code: {e.returncode}. Stderr: {e.stderr}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse ffprobe JSON for {filepath}: {e}")
        return None
    except FileNotFoundError:
        logging.error("ffprobe command not found. Please ensure FFmpeg (with ffprobe) is installed and in your system PATH.")
        # Potentially raise a custom exception or exit, as this is a critical dependency
        return None

def determine_track_indices(streams_info):
    """Parses ffprobe stream info to find English audio and subtitle track indices."""
    eng_audio_idx = None
    eng_subtitle_idx = None
    
    if not streams_info or 'streams' not in streams_info:
        logging.warning("No streams information available to determine track indices.")
        return None, None

    # FFmpeg stream indices are usually absolute within the input file context.
    # ffprobe provides an 'index' field for each stream.
    for stream in streams_info['streams']:
        lang = stream.get('tags', {}).get('language', '').lower()
        stream_index_str = str(stream['index']) # Ensure it's a string for ffmpeg map

        if stream['codec_type'] == 'audio':
            if lang == 'eng':
                if eng_audio_idx is None: # Take the first one found
                    eng_audio_idx = stream_index_str
                    logging.debug(f"Found English audio track: index {eng_audio_idx}")
            # If no English audio found yet, consider first audio track as a fallback (handled in command construction)
        
        elif stream['codec_type'] == 'subtitle':
            if lang == 'eng':
                if stream['codec_name'] in ['srt', 'ass', 'ssa', 'subrip', 'mov_text']:
                    if eng_subtitle_idx is None:
                        eng_subtitle_idx = stream_index_str
                        logging.debug(f"Found English text subtitle track: index {eng_subtitle_idx}, codec {stream['codec_name']}")
    
    return eng_audio_idx, eng_subtitle_idx

def verify_output(filepath):
    """Basic verification of the output file using ffprobe."""
    logging.debug(f"Verifying output file: {filepath}")
    stream_info = get_stream_info(filepath)
    if not stream_info or 'streams' not in stream_info:
        logging.error(f"Verification failed: Could not get stream info for {filepath}")
        return False
    
    has_hevc_video = False
    for stream in stream_info['streams']:
        if stream.get('codec_type') == 'video' and stream.get('codec_name') == 'hevc':
            has_hevc_video = True
            break
    
    if not has_hevc_video:
        logging.error(f"Verification failed: No HEVC video stream found in {filepath}")
        return False
    
    logging.info(f"Output file {filepath} verified successfully (contains HEVC video stream).")
    return True

def convert_file(input_filepath, config):
    """
    Converts a single video file to H.265 MP4.
    Manages ffprobe, ffmpeg command construction, execution, and safe file replacement.
    """
    base, input_ext = os.path.splitext(input_filepath)
    final_output_filepath = base + ".mp4"
    temp_output_filepath = base + ".temp.mp4"

    logging.info(f"Starting conversion for: {input_filepath}")
    logging.debug(f"Config for this conversion: {config}")

    if config.get('dry_run', False):
        logging.info(f"[DRY RUN] Would process file: {input_filepath}")
        logging.info(f"[DRY RUN] Output would be: {final_output_filepath}")
        # Simulate ffprobe and ffmpeg command construction for logging
        stream_info = get_stream_info(input_filepath) # Still run ffprobe in dry_run to show what would happen
        if not stream_info:
            logging.warning(f"[DRY RUN] ffprobe failed for {input_filepath}. Cannot show detailed command.")
            return True # Simulate success for dry run, as no files are changed
        
        eng_audio_idx, eng_sub_idx = determine_track_indices(stream_info)
        # Log the determined indices
        if eng_audio_idx:
            logging.info(f"[DRY RUN] Determined English audio track index: {eng_audio_idx}")
        else:
            logging.info("[DRY RUN] No English audio track found; will use first available.")
        if eng_sub_idx:
            logging.info(f"[DRY RUN] Determined English subtitle track index: {eng_sub_idx}")
        else:
            logging.info("[DRY RUN] No English subtitle track found or suitable.")
            
        # Construct and log the command (simplified for dry run logging)
        ffmpeg_cmd_dry_run = build_ffmpeg_command(input_filepath, temp_output_filepath, stream_info, eng_audio_idx, eng_sub_idx, config)
        if ffmpeg_cmd_dry_run:
             logging.info(f"[DRY RUN] FFmpeg command that would be executed: {' '.join(ffmpeg_cmd_dry_run)}")
        else:
            logging.error("[DRY RUN] Failed to construct FFmpeg command.")
            return False # Indicate failure to construct command even in dry run
        
        logging.info(f"[DRY RUN] Would attempt to replace original file {input_filepath} with {final_output_filepath} upon successful conversion.")
        return True # Simulate success for dry run file operations

    stream_info = get_stream_info(input_filepath)
    if not stream_info:
        logging.error(f"Could not get stream info for {input_filepath}. Skipping conversion.")
        return False

    eng_audio_idx, eng_sub_idx = determine_track_indices(stream_info)

    ffmpeg_cmd = build_ffmpeg_command(input_filepath, temp_output_filepath, stream_info, eng_audio_idx, eng_sub_idx, config)
    if not ffmpeg_cmd:
        logging.error(f"Failed to construct FFmpeg command for {input_filepath}. Skipping.")
        return False

    logging.info(f"Executing FFmpeg command for {input_filepath}: {' '.join(ffmpeg_cmd)}")

    try:
        # Ensure temp file from previous failed run is removed if it exists
        if os.path.exists(temp_output_filepath):
            logging.warning(f"Removing pre-existing temporary file: {temp_output_filepath}")
            os.remove(temp_output_filepath)
            
        process = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=False, encoding='utf-8', errors='replace')
        
        if process.returncode == 0:
            logging.info(f"Successfully converted {input_filepath} to {temp_output_filepath}")
            
            if not verify_output(temp_output_filepath):
                logging.error(f"Verification failed for {temp_output_filepath}. Will not replace original.")
                if os.path.exists(temp_output_filepath): os.remove(temp_output_filepath)
                return False

            # Safe file replacement
            try:
                if os.path.exists(input_filepath):
                    if input_filepath.lower() == final_output_filepath.lower():
                        # This case means the input was already an MP4. We are replacing it.
                        # We need to remove the original before renaming temp to final, or rename won't work as expected.
                        # However, if the input_filepath is the same as final_output_filepath, 
                        # and we are about to rename temp_output_filepath to final_output_filepath,
                        # we must ensure the original is gone if it's not the same actual file object as temp.
                        # A more robust way is to rename to a unique intermediate name, then delete original, then rename intermediate to final.
                        # For simplicity here, we assume os.rename will overwrite if final_output_filepath is the target.
                        # If input_filepath and final_output_filepath are the same, os.remove(input_filepath) is safe before os.rename
                        # as long as temp_output_filepath is different.
                        logging.info(f"Original file {input_filepath} is an MP4. It will be replaced by the new conversion.")
                        # To be absolutely safe, remove original if it's the same name as the final output before rename.
                        # This handles case where input is 'movie.mp4' and output is 'movie.mp4'.
                        # os.remove(input_filepath) # This might be redundant if os.rename overwrites, but safer.
                    else:
                        # Original was not MP4 (e.g. MKV), so delete it.
                        logging.info(f"Removing original file: {input_filepath}")
                        os.remove(input_filepath)
                
                os.rename(temp_output_filepath, final_output_filepath)
                logging.info(f"Successfully replaced original file with {final_output_filepath}")
                return True
            except OSError as e:
                logging.error(f"Error during file replacement for {input_filepath} -> {final_output_filepath}: {e}")
                if os.path.exists(temp_output_filepath): # Cleanup temp if rename failed
                     logging.warning(f"Attempting to remove temp file {temp_output_filepath} after failed rename.")
                     os.remove(temp_output_filepath)
                return False
        else:
            error_message_lines = process.stderr.strip().splitlines()
            concise_error = "\n".join(error_message_lines[-10:]) # Last 10 lines for more context
            logging.error(f"FFmpeg failed for {input_filepath} (exit code {process.returncode}). Error: {concise_error}")
            logging.debug(f"Full FFmpeg stderr for {input_filepath}:\n{process.stderr}")
            if os.path.exists(temp_output_filepath):
                os.remove(temp_output_filepath)
            return False
    except FileNotFoundError:
        logging.error("ffmpeg command not found. Please ensure FFmpeg is installed and in your system PATH.")
        return False # Critical dependency missing
    except Exception as e:
        logging.critical(f"An unexpected error occurred during FFmpeg execution or file operations for {input_filepath}: {e}", exc_info=True)
        if os.path.exists(temp_output_filepath):
            os.remove(temp_output_filepath)
        return False

def build_ffmpeg_command(input_filepath, temp_output_filepath, stream_info, eng_audio_idx, eng_sub_idx, config):
    """Constructs the FFmpeg command list based on configuration and stream info."""
    ffmpeg_cmd = ['ffmpeg', '-y', '-i', input_filepath]

    # Video Stream Mapping & Encoding
    ffmpeg_cmd.extend(['-map', '0:v:0']) # Map first video stream
    gpu_type = config.get('gpu_type', 'cpu')
    quality_level = str(config.get('quality_level', 23))
    h265_profile = config.get('h265_profile', 'main')

    if gpu_type == 'nvidia':
        ffmpeg_cmd.extend(['-c:v', 'hevc_nvenc', '-preset', 'p5', '-cq', quality_level, '-profile:v', h265_profile])
        if h265_profile == 'main10':
            ffmpeg_cmd.extend(['-pix_fmt', 'p010le'])
        # Consider: '-tune', 'uhq' after benchmarking
    elif gpu_type == 'intel':
        ffmpeg_cmd.extend(['-c:v', 'hevc_qsv', '-preset:v', 'medium', '-global_quality', quality_level, '-profile:v', h265_profile])
        if h265_profile == 'main10':
            ffmpeg_cmd.extend(['-pix_fmt', 'p010le'])
        # Consider: '-look_ahead', '1'
    elif gpu_type == 'amd':
        ffmpeg_cmd.extend(['-c:v', 'hevc_amf', '-rc', 'cqp', '-qp_i', quality_level, '-qp_p', quality_level, '-qp_b', quality_level, '-usage', 'transcoding', '-profile', h265_profile])
        if h265_profile == 'main10':
            ffmpeg_cmd.extend(['-pix_fmt', 'p010le'])
            logging.warning("Using 'main10' profile with AMD AMF. Test output thoroughly for color metadata issues. Consider NVENC/QSV for critical 10-bit content.")
    else: # CPU (libx265)
        ffmpeg_cmd.extend(['-c:v', 'libx265', '-preset', 'medium', '-crf', quality_level, '-profile:v', h265_profile])
        if h265_profile == 'main10':
            ffmpeg_cmd.extend(['-pix_fmt', 'yuv420p10le'])
        # Consider: '-tune', 'fastdecode'

    # Audio Stream Mapping & Encoding
    audio_codec = config.get('audio_codec', 'aac')
    audio_quality = config.get('audio_quality', '2')
    audio_stream_mapped = False

    if eng_audio_idx is not None:
        ffmpeg_cmd.extend(['-map', f"0:{eng_audio_idx}"])
        logging.info(f"Mapping English audio stream index: {eng_audio_idx}")
        audio_stream_mapped = True
    else:
        # Fallback: map first audio track if it exists, ffmpeg will error if no audio track at all
        ffmpeg_cmd.extend(['-map', '0:a:0?']) 
        logging.warning(f"No English audio track found for {input_filepath}. Attempting to map first available audio track (0:a:0?).")
        # If 0:a:0? maps something, it becomes audio output stream 0
        # If not, there will be no audio output stream unless another -map 0:a... is added
        # We rely on this single map for the primary audio.
        audio_stream_mapped = True # We are attempting to map, even if it might not exist

    if audio_stream_mapped: # Only add codec and disposition if an audio track was mapped
        if audio_codec == 'copy':
            ffmpeg_cmd.extend(['-c:a:0', 'copy']) # Apply to the first audio output stream
        else:
            ffmpeg_cmd.extend(['-c:a:0', audio_codec, '-q:a:0', audio_quality]) # Apply to the first audio output stream
        ffmpeg_cmd.extend(['-disposition:a:0', 'default']) # Apply to the first audio output stream
    else:
        logging.warning(f"No audio stream could be mapped for {input_filepath}. Output will have no audio.")

    # Subtitle Stream Mapping & Encoding
    if eng_sub_idx is not None:
        ffmpeg_cmd.extend(['-map', f"0:{eng_sub_idx}", '-c:s:0', 'mov_text', '-disposition:s:0', 'default']) # Apply to first subtitle output stream
        logging.info(f"Mapping English subtitle stream index: {eng_sub_idx} as mov_text.")
    else:
        logging.info(f"No suitable English subtitle track found or selected for {input_filepath}. No subtitles will be embedded.")

    # Chapter Mapping
    ffmpeg_cmd.extend(['-map_chapters', '0'])

    # Add movflags for web optimization
    ffmpeg_cmd.extend(['-movflags', '+faststart'])

    ffmpeg_cmd.append(temp_output_filepath)
    return ffmpeg_cmd