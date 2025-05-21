import os
import logging
from ffmpeg_wrapper import convert_file # Corrected import

VIDEO_EXTENSIONS = ('.mkv', '.avi', '.mov', '.ts', '.mpg', '.flv', '.wmv', '.mp4') # Added .mp4 as per spec

def process_media_library(root_dir, config):
    """Traverses directory, identifies video files, and orchestrates their conversion, with GUI updates."""
    update_queue = config.get('update_queue')

    files_to_process_fullpaths = []
    if update_queue:
        update_queue.put(("status_update", "Scanning for video files..."))
    # First pass: Collect all files
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            base, ext = os.path.splitext(filename)
            if ext.lower() in VIDEO_EXTENSIONS:
                files_to_process_fullpaths.append(os.path.join(dirpath, filename))
    
    total_files = len(files_to_process_fullpaths)
    if update_queue:
        update_queue.put(("progress_max", total_files))
        update_queue.put(("pending_files_list", files_to_process_fullpaths)) # Send full paths
        update_queue.put(("status_update", f"Found {total_files} video files to potentially process."))
        update_queue.put(("log", f"Found {total_files} potential video files in {root_dir}."))

    processed_count = 0
    skipped_count = 0
    failed_count = 0

    logging.info(f"Starting to process media library in {root_dir}. Found {total_files} potential videos.")

    for i, input_filepath in enumerate(files_to_process_fullpaths):
        current_fileno = i + 1
        base_name = os.path.basename(input_filepath)
        dir_path = os.path.dirname(input_filepath)
        file_status = "UNKNOWN" # Default status
        
        if update_queue:
            # Notify GUI that this file is starting processing, so it can be removed from pending
            update_queue.put(("file_processing_start", input_filepath)) 
            update_queue.put(("status_update", f"Processing file {current_fileno}/{total_files}: {base_name}"))

        final_output_filepath = os.path.join(dir_path, os.path.splitext(base_name)[0] + ".mp4")

        if config.get('skip_existing', False) and os.path.exists(final_output_filepath):
            if input_filepath.lower() == final_output_filepath.lower():
                log_msg = f"Skipping re-encoding of MP4: {base_name}"
                file_status = "SKIPPED (already MP4)"
                skipped_count += 1
            elif input_filepath.lower() != final_output_filepath.lower():
                log_msg = f"Output {os.path.basename(final_output_filepath)} exists for {base_name}. Skipping."
                file_status = "SKIPPED (exists)"
                skipped_count += 1
            # This 'else' for the skip_existing logic was problematic; removed it.
            # If it's skipped, we log and continue.
            
            logging.info(log_msg)
            if update_queue: update_queue.put(("log", log_msg))
            if update_queue: update_queue.put(("file_processed_status", (input_filepath, file_status)))
            if update_queue: update_queue.put(("progress_update", (current_fileno, total_files)))
            continue
        
        log_msg_processing = f"Starting conversion for ({current_fileno}/{total_files}): {input_filepath}"
        logging.info(log_msg_processing)
        # GUI log will get more detailed logs from ffmpeg_wrapper via TextHandler

        try:
            conversion_success = convert_file(input_filepath, config)
            if conversion_success:
                processed_count += 1
                file_status = "CONVERTED"
            else:
                failed_count += 1
                file_status = "FAILED"
        except Exception as e:
            err_msg = f"Unexpected error processing {base_name}: {e}"
            logging.error(err_msg, exc_info=True)
            if update_queue: update_queue.put(("log", f"ERROR: {err_msg}"))
            failed_count += 1
            file_status = "ERROR"
        
        if update_queue:
            update_queue.put(("file_processed_status", (input_filepath, file_status)))
            update_queue.put(("progress_update", (current_fileno, total_files)))

    summary_msg = f"Scanned: {total_files}, Converted: {processed_count}, Skipped: {skipped_count}, Failed: {failed_count}"
    logging.info(f"Finished processing media library. {summary_msg}")
    
    results = {
        'scanned': total_files,
        'processed': processed_count,
        'skipped': skipped_count,
        'failed': failed_count,
        'summary_string': summary_msg
    }

    if update_queue:
        update_queue.put(("conversion_complete", summary_msg))
        if total_files > 0: # Ensure progress bar completes if files were processed
            update_queue.put(("progress_update", (total_files, total_files)))

    return results

# Remove placeholder as it's replaced by ffmpeg_wrapper.convert_file
# def convert_file_placeholder(input_path, output_path_final_name, gpu_type):
#     # This is a placeholder for the detailed conversion logic in section C
#     logging.info(f"Placeholder: Would convert {input_path} to {output_path_final_name} using {gpu_type}")
#     # Actual implementation will call ffprobe, build ffmpeg command, execute, verify, and replace.
#     pass