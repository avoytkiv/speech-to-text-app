import os
import time
import requests
import logging
import sys
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv
import swagger_client
from swagger_client.models import DiarizationProperties, TranscriptionProperties
from audio_utils import split_audio_file  

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
        format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p %Z")

# Load environment variables
dotenv_path = '/workspaces/speech-to-text-app/.env'
load_dotenv(dotenv_path)

MODEL_REFERENCE = '6df6b743-91a3-4e6f-87fe-680191947ee2'
SUBSCRIPTION_KEY = os.environ.get("SUBSCRIPTION_KEY") 
SERVICE_REGION = os.environ.get("SERVICE_REGION")

# Initialize Azure Blob Service Client
account_url = "https://speechtotextblobstorage.blob.core.windows.net"
default_credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url, credential=default_credential)

def create_container(container_name):
    logging.info(f"Creating container: {container_name}")
    container_client = blob_service_client.create_container(container_name)
    return container_client

def upload_file_to_blob(container_name, file_path):
    logging.info(f"Uploading file to blob: {file_path} in container: {container_name}")
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=os.path.basename(file_path))
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data)
    blob_url = blob_client.url
    logging.info(f"File uploaded successfully, Blob URL: {blob_url}")
    return blob_url

def transcribe_audio_with_azure_urls(blob_urls):
    logging.info(f"Starting transcription for audio from provided URLs.")

    configuration = swagger_client.Configuration()
    configuration.api_key["Ocp-Apim-Subscription-Key"] = SUBSCRIPTION_KEY
    configuration.host = f"https://{SERVICE_REGION}.api.cognitive.microsoft.com/speechtotext/v3.2"
    logging.debug(f"API Host: {configuration.host}")

    client = swagger_client.ApiClient(configuration)
    api = swagger_client.CustomSpeechTranscriptionsApi(api_client=client)

    if MODEL_REFERENCE is None:
        logging.error("Custom model IDs must be set when using custom models")
        sys.exit()

    model = {'self': f'{client.configuration.host}/models/base/{MODEL_REFERENCE}'}

    diarization_props = DiarizationProperties(
        speakers={'minCount': 1, 'maxCount': 3}
    )
    properties = TranscriptionProperties(
        word_level_timestamps_enabled=False,
        display_form_word_level_timestamps_enabled=False,
        diarization_enabled=True,
        diarization=diarization_props,
        punctuation_mode="DictatedAndAutomatic",
        profanity_filter_mode="Masked"
    )

    transcription_definition = swagger_client.Transcription(
        display_name="URLs Transcription",
        description="Azure Speech Service Transcription for provided URLs",
        locale="uk-UA",
        model=model,
        content_urls=blob_urls,
        properties=properties
    )

    created_transcription, status, headers = api.transcriptions_create_with_http_info(transcription=transcription_definition)
    transcription_id = headers["location"].split("/")[-1]
    logging.info(f"Created transcription with ID: {transcription_id}")

    completed = False
    while not completed:
        time.sleep(5)
        transcription = api.transcriptions_get(transcription_id)
        logging.debug(f"Transcription status: {transcription.status}")
        if transcription.status in ("Failed", "Succeeded"):
            logging.info(f"Final transcription status: {transcription.status}")
            completed = True

        if transcription.status == "Succeeded":
            pag_files = api.transcriptions_list_files(transcription_id)
            logging.debug(f"Files associated with transcription: {pag_files}")
            all_plain_text = []
            all_speaker_info = []
            # Process each file's results as needed
            for file_data in pag_files.values:
                if file_data.kind == "Transcription":
                    results_url = file_data.links.content_url
                    transcription_json = download_transcription(results_url)
                    plain_text, speaker_info = extract_plain_text_and_speakers(transcription_json)
                    all_plain_text.append(plain_text)
                    all_speaker_info.extend(speaker_info)
                    save_transcription(plain_text, speaker_info, file_data.name)
            return "\n\n".join(all_plain_text), all_speaker_info

    logging.error(f"Transcription failed: {transcription.properties.error.message}")
    return "Transcription failed", []

def download_transcription(results_url):
    logging.info(f"Downloading transcription from URL: {results_url}")
    response = requests.get(results_url)
    response.raise_for_status()
    return response.json()

def extract_plain_text_and_speakers(transcription_json):
    logging.debug("Extracting plain text and speaker information from transcription JSON")
    combined_phrases = transcription_json.get("combinedRecognizedPhrases", [])
    recognized_phrases = transcription_json.get("recognizedPhrases", [])
    
    plain_text = combined_phrases[0].get("display", "") if combined_phrases else "No transcription text found."
    
    speaker_info = []
    last_speaker = None
    last_text = None

    for phrase in recognized_phrases:
        speaker_id = phrase.get("speaker", "Unknown")
        display_text = phrase["nBest"][0].get("display", "")

        if speaker_id == last_speaker:
            last_text += f" {display_text}"
        else:
            if last_speaker is not None:
                speaker_info.append(f"Speaker {last_speaker}: {last_text}")
            last_speaker = speaker_id
            last_text = display_text
    
    if last_speaker is not None:
        speaker_info.append(f"Speaker {last_speaker}: {last_text}")
    
    logging.debug("Extraction completed")
    return plain_text, speaker_info

def save_transcription(plain_text, speaker_info, file_name):
    logging.info(f"Saving transcription with file name: {file_name}")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join("transcriptions", f"{file_name}_{timestamp}.txt")
    
    if not os.path.exists("transcriptions"):
        os.makedirs("transcriptions")
        logging.debug("Created 'transcriptions' directory")
    
    with open(file_path, "w") as f:
        f.write("Transcription Text:\n")
        f.write(plain_text + "\n\n")
        f.write("Speaker Information:\n")
        for info in speaker_info:
            f.write(info + "\n")

    logging.info(f"Transcription saved to {file_path}")

def process_audio_file(file_path):
    # Step 1: Split the audio file into smaller chunks
    chunk_paths = split_audio_file(file_path, max_file_size=5 * 1024 * 1024) 

    # Step 2: Create a container in Azure Blob Storage
    container_name = f"audio-chunks-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    create_container(container_name)

    # Step 3: Upload each chunk to the container and gather their URLs
    blob_urls = [upload_file_to_blob(container_name, chunk_path) for chunk_path in chunk_paths]

    # Step 4: Transcribe all chunks using their URLs
    combined_text, speaker_info = transcribe_audio_with_azure_urls(blob_urls)

    return combined_text, speaker_info
