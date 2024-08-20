from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
import os
import swagger_client
from swagger_client.models import DiarizationProperties, TranscriptionProperties
import time
import requests
from dotenv import load_dotenv
import logging
import sys
import json
from datetime import datetime

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
        format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p %Z")

dotenv_path = '/workspaces/speech-to-text-app/.env'
load_dotenv(dotenv_path)

MODEL_REFERENCE = '6df6b743-91a3-4e6f-87fe-680191947ee2'
AZURE_STORAGE_CONNECTION_STRING = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
SUBSCRIPTION_KEY = os.environ.get("SUBSCRIPTION_KEY") 
SERVICE_REGION = os.environ.get("SERVICE_REGION")

account_url = "https://speechtotextblobstorage.blob.core.windows.net"
default_credential = DefaultAzureCredential()

blob_service_client = BlobServiceClient(account_url, credential=default_credential)

def create_container(container_name):
    container_client = blob_service_client.create_container(container_name)
    return container_client

def upload_file_to_blob(container_name, file_path):
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=os.path.basename(file_path))
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data)
    sas_url = blob_client.url
    return sas_url

def transcribe_audio_with_azure(blob_url):
    print(f"Transcribing audio from: {blob_url}")
    configuration = swagger_client.Configuration()
    configuration.api_key["Ocp-Apim-Subscription-Key"] = SUBSCRIPTION_KEY
    configuration.host = f"https://{SERVICE_REGION}.api.cognitive.microsoft.com/speechtotext/v3.2"
    logging.debug(f"Host: {configuration.host}")

    client = swagger_client.ApiClient(configuration)
    api = swagger_client.CustomSpeechTranscriptionsApi(api_client=client)

    if MODEL_REFERENCE is None:
        logging.error("Custom model ids must be set when using custom models")
        sys.exit()

    model = {'self': f'{client.configuration.host}/models/base/{MODEL_REFERENCE}'}

    diarization_props = DiarizationProperties(
        speakers={'minCount': 1, 'maxCount': 3}
    )
    properties = TranscriptionProperties(
        # destination_container_url="https://your_storage_account.blob.core.windows.net/your_container_name",
        word_level_timestamps_enabled=False,
        display_form_word_level_timestamps_enabled=False,
        diarization_enabled=True,
        diarization=diarization_props,
        punctuation_mode="DictatedAndAutomatic",
        profanity_filter_mode="Masked"
    )
    transcription_definition = swagger_client.Transcription(
        display_name="Transcription",
        description="Azure Speech Service Transcription",
        locale="uk-UA",
        model=model,
        content_urls=[blob_url],
        properties=properties
    )

    created_transcription, status, headers = api.transcriptions_create_with_http_info(transcription=transcription_definition)
    transcription_id = headers["location"].split("/")[-1]

    completed = False
    while not completed:
        time.sleep(5)
        transcription = api.transcriptions_get(transcription_id)
        if transcription.status in ("Failed", "Succeeded"):
            print(f"Transcription status: {transcription.status}")
            completed = True

        if transcription.status == "Succeeded":
            pag_files = api.transcriptions_list_files(transcription_id)
            print(f"Files: {pag_files}")
            for file_data in pag_files.values:
                if file_data.kind == "Transcription":
                    results_url = file_data.links.content_url
                    results = requests.get(results_url)
                    transcription_json = download_transcription(results_url)
                    plain_text, speaker_info = extract_plain_text_and_speakers(transcription_json)
                    save_transcription(plain_text, speaker_info, file_data.name)
                    return plain_text, speaker_info
        elif transcription.status == "Failed":
            return f"Transcription failed: {transcription.properties.error.message}"

def download_transcription(results_url):
    """
    Downloads the transcription JSON file from the provided URL.
    """
    response = requests.get(results_url)
    response.raise_for_status()
    return response.json()

def extract_plain_text_and_speakers(transcription_json):
    """
    Extracts plain text and speaker information from the transcription JSON response.
    Combines consecutive phrases by the same speaker into single entries.
    """
    combined_phrases = transcription_json.get("combinedRecognizedPhrases", [])
    recognized_phrases = transcription_json.get("recognizedPhrases", [])
    
    # Extract plain text
    plain_text = combined_phrases[0].get("display", "") if combined_phrases else "No transcription text found."
    
    # Extract and combine speaker information
    speaker_info = []
    last_speaker = None
    last_text = None

    for phrase in recognized_phrases:
        speaker_id = phrase.get("speaker", "Unknown")
        display_text = phrase["nBest"][0].get("display", "")

        if speaker_id == last_speaker:
            # Combine with the last entry if the speaker is the same
            last_text += f" {display_text}"
        else:
            if last_speaker is not None:
                speaker_info.append(f"Speaker {last_speaker}: {last_text}")
            last_speaker = speaker_id
            last_text = display_text
    
    # Append the last speaker's text
    if last_speaker is not None:
        speaker_info.append(f"Speaker {last_speaker}: {last_text}")
    
    return plain_text, speaker_info


def save_transcription(plain_text, speaker_info, file_name):
    """
    Saves the transcription text and speaker information to a local file with a timestamp.
    """
    # Get the current timestamp in a readable format
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create the file name with the timestamp
    file_path = os.path.join("transcriptions", f"{file_name}_{timestamp}.txt")
    
    # Ensure the directory exists
    if not os.path.exists("transcriptions"):
        os.makedirs("transcriptions")

    # Write the transcription and speaker information to the file
    with open(file_path, "w") as f:
        f.write("Transcription Text:\n")
        f.write(plain_text + "\n\n")
        f.write("Speaker Information:\n")
        for info in speaker_info:
            f.write(info + "\n")

    print(f"Transcription saved to {file_path}")