import openai
import os

# Load OpenAI API key from environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

def transcribe_audio_with_openai(file_path):
    # Open the audio file
    with open(file_path, "rb") as audio_file:
        # Transcribe the audio using OpenAI's Whisper API
        transcription = openai.Audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcription["text"]
