import streamlit as st
import openai
from openai import OpenAI
import os
from datetime import datetime

# Set the directory where audio files will be saved
UPLOAD_DIR = "uploaded_audios"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

def save_uploaded_file(uploaded_file):
    # Create a unique filename using the current time
    current_time = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{current_time}_{uploaded_file.name}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save the file to the specified directory
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return filepath

def transcribe_audio_with_openai(file_path):
    # Open the audio file
    with open(file_path, "rb") as audio_file:
        client = OpenAI()
        # Transcribe the audio using OpenAI's updated API
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    # Correctly accessing the transcription text from the dictionary
    return transcription


# Streamlit UI
st.title("Audio Upload and Transcription with OpenAI Whisper")

# Create a file uploader that accepts audio files
uploaded_file = st.file_uploader("Choose an audio file", type=["wav", "mp3", "mp4", "m4a", "webm"])

if uploaded_file is not None:
    # Save the uploaded file
    file_path = save_uploaded_file(uploaded_file)
    
    # Display a success message and the file path
    st.success(f"File saved at {file_path}")
    st.audio(file_path)  # Optionally, play the audio file within the app
    
    # Transcribe the audio file using OpenAI's updated API
    with st.spinner('Transcribing...'):
        transcription = transcribe_audio_with_openai(file_path)
    
    # Display the transcription
    st.write("**Transcription:**")
    st.text_area("", transcription, height=300)
