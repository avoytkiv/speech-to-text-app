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
                    return results.content.decode('utf-8')
        elif transcription.status == "Failed":
            return f"Transcription failed: {transcription.properties.error.message}"
