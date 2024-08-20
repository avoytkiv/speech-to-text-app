from pydub import AudioSegment
import sys
import os
import logging

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
        format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p %Z")

# Define a constant for the maximum file size in bytes (25 MB = 25 * 1024 * 1024)
MAX_FILE_SIZE = 1 * 1024 * 1024

def split_audio_file(file_path, max_file_size=MAX_FILE_SIZE):
    """
    Splits an audio file into smaller chunks if it exceeds the maximum file size.

    :param file_path: Path to the original audio file.
    :param max_file_size: Maximum size of each chunk in bytes.
    :return: List of file paths to the audio chunks.
    """
    logging.info(f"Checking if file needs splitting: {file_path}")

    # Get the file size
    file_size = os.path.getsize(file_path)

    if file_size <= max_file_size:
        logging.info("File size is within the limit; no need to split.")
        return [file_path]

    logging.info(f"File size ({file_size} bytes) exceeds the maximum limit of {max_file_size} bytes. Splitting the file...")

    # Load the audio file using pydub
    file_extension = os.path.splitext(file_path)[1][1:]
    audio = AudioSegment.from_file(file_path, format=file_extension)
    file_duration = len(audio)  # Duration in milliseconds

    # Calculate the number of chunks needed
    num_chunks = file_size // max_file_size + 1
    chunk_duration = file_duration // num_chunks  # Duration per chunk in milliseconds

    # Create a directory for the chunks
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_dir = os.path.join(os.path.dirname(file_path), f"{base_name}_chunks")
    os.makedirs(output_dir, exist_ok=True)

    # Split the audio into chunks
    chunk_paths = []
    for i in range(num_chunks):
        start_time = i * chunk_duration
        end_time = start_time + chunk_duration if i < num_chunks - 1 else file_duration

        chunk = audio[start_time:end_time]
        chunk_filename = f"{base_name}_chunk{i+1}.wav"
        chunk_path = os.path.join(output_dir, chunk_filename)
        chunk.export(chunk_path, format="wav")

        chunk_paths.append(chunk_path)
        logging.info(f"Created chunk: {chunk_path} (Duration: {len(chunk) / 1000} seconds)")

    return chunk_paths


if __name__ == "__main__":
    file_path = "/workspaces/speech-to-text-app/uploaded_audios/test.m4a"
    split_audio_file(file_path)
