import os
import logging
from ffmpeg_wrapper import convert_file # Corrected import

VIDEO_EXTENSIONS = ('.mkv', '.avi', '.mov', '.ts', '.mpg', '.flv', '.wmv', '.mp4') # Added .mp4 as per spec

def process_media_library(root_dir, config):
    """Traverses directory, identifies video files, and orchestrates their conversion."""
    processed_count = 0
    skipped_count = 0
    failed_count = 0
    scanned_count = 0 # Added for summary

    logging.info(f"Starting to process media library in root directory: {root_dir}")

    for dirpath, dirnames, filenames in os.walk(root_dir):
        logging.debug(f"Scanning directory: {dirpath}")
        for filename in filenames:
            scanned_count +=1
            base, ext = os.path.splitext(filename)
            input_filepath = os.path.join(dirpath, filename)

            if ext.lower() not in VIDEO_EXTENSIONS:
                logging.debug(f"Skipping non-video file: {input_filepath}")
                continue

            # Construct final output path
            final_output_filepath = os.path.join(dirpath, base + ".mp4")

            # Resumability Logic
            if config.get('skip_existing', False) and os.path.exists(final_output_filepath):
                # If input is MP4, and output is same MP4, skip_existing means we don't re-encode.
                # If input is MKV, and output MP4 exists, skip_existing means we skip.
                if input_filepath.lower() == final_output_filepath.lower():
                    logging.info(f"Skipping re-encoding of already existing MP4: {input_filepath} due to --skip_existing flag.")
                    skipped_count += 1
                    continue
                elif input_filepath.lower() != final_output_filepath.lower(): # e.g. movie.mkv -> movie.mp4
                    logging.info(f"Output file {final_output_filepath} already exists for {input_filepath}. Skipping due to --skip_existing flag.")
                    skipped_count += 1
                    continue
            
            logging.info(f"Processing video file: {input_filepath}")
            try:
                # Pass the whole config object to convert_file
                conversion_success = convert_file(input_filepath, config)
                if conversion_success:
                    processed_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                logging.error(f"An unexpected error occurred while processing {input_filepath}: {e}", exc_info=True)
                failed_count += 1

    logging.info(f"Finished processing media library. Scanned: {scanned_count}, Converted: {processed_count}, Skipped: {skipped_count}, Failed: {failed_count}")
    return {
        'scanned': scanned_count,
        'processed': processed_count, # 'converted' in main.py log
        'skipped': skipped_count,
        'failed': failed_count
    }

# Remove placeholder as it's replaced by ffmpeg_wrapper.convert_file
# def convert_file_placeholder(input_path, output_path_final_name, gpu_type):
#     # This is a placeholder for the detailed conversion logic in section C
#     logging.info(f"Placeholder: Would convert {input_path} to {output_path_final_name} using {gpu_type}")
#     # Actual implementation will call ffprobe, build ffmpeg command, execute, verify, and replace.
#     pass