import streamlit as st
from file_utils import save_uploaded_file
from openai_utils import transcribe_audio_with_openai
from azure_utils import process_audio_file
import uuid

# Streamlit UI
st.title("Audio Upload and Transcription Service")

# Option to select the transcription service
service_option = st.radio(
    "Choose transcription service:",
    ("OpenAI Whisper", "Azure Speech Service")
)

# Create a file uploader that accepts audio files
uploaded_file = st.file_uploader("Choose an audio file", type=["wav", "mp3", "mp4", "m4a", "webm"])

if uploaded_file is not None:
    # Save the uploaded file
    file_path = save_uploaded_file(uploaded_file)
    
    # Display a success message and the file path
    st.success(f"File saved at {file_path}")
    st.audio(file_path)  # Optionally, play the audio file within the app
    
    if service_option == "OpenAI Whisper":
        with st.spinner('Transcribing with OpenAI Whisper...'):
            transcription = transcribe_audio_with_openai(file_path)
    elif service_option == "Azure Speech Service":
        with st.spinner('Processing with Azure Speech Service...'):
            transcription, speaker_info = process_audio_file(file_path)
    
    # Display the transcription
    st.write("**Transcription:**")
    st.text_area("", transcription, height=300)
