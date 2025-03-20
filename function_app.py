import azure.functions as func
import azure.durable_functions as df
import logging
import os
import json
from datetime import datetime, timedelta

from services.storage_service import AzureBlobStorageService
from services.podcast_summarizer import AzureOpenAISummarizer
from services.batch_transcriber import BatchTranscriber
from models.podcast import ProcessingStatus

app = df.DFApp(http_auth_level=func.AuthLevel.FUNCTION)

# Client API - HTTP Trigger for file upload


@app.route(route="podcast-summarizer/process-audio", auth_level=func.AuthLevel.FUNCTION)
@app.durable_client_input(client_name="starter")
async def upload_podcast(req: func.HttpRequest, starter: df.DurableOrchestrationClient) -> func.HttpResponse:
    """
    Upload endpoint that starts the transcription orchestration
    """
    try:
        # Get audio file from request
        audio_file = req.files.get('file')
        if not audio_file:
            return func.HttpResponse(
                json.dumps({"error": "No file uploaded"}),
                mimetype="application/json",
                status_code=400
            )

        # Generate unique ID
        podcast_id = f"podcast-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

        # Save file to blob storage
        storage = AzureBlobStorageService(
            connection_string=os.environ["AZURE_STORAGE_CONNECTION_STRING"])
        file_url = await storage.upload_to_blob_storage(file=audio_file, container_name=podcast_id)
        logging.info(f"Saved file: {file_url}")

        # Start orchestration
        instance_id = await starter.start_new("transcribe_orchestrator", None, file_url)

        # .get_body().decode('utf-8')
        return starter.create_check_status_response(req, instance_id)

    except Exception as e:
        logging.error(f"Error in upload: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


def create_response(body, status_code):
    """Helper function to create consistent HTTP responses"""
    return func.HttpResponse(
        json.dumps(body),
        mimetype="application/json",
        status_code=status_code
    )

# Durable Functions Orchestrator


@app.orchestration_trigger(context_name="context")
def transcribe_orchestrator(context: df.DurableOrchestrationContext):
    """
    Main orchestrator function that coordinates the transcription workflow
    """
    fileUrl = context.get_input()
    try:
        # 1. Start transcription and get transcription ID
        transcriptionId = yield context.call_activity("start_transcription", fileUrl)
        if not transcriptionId:
            raise Exception("Transcription could not be started")
        # 2. Poll for completion (retry every 30 seconds for up to 2 hours)
        expiry_time = context.current_utc_datetime + timedelta(hours=2)

        while context.current_utc_datetime < expiry_time:
            # Check transcription status
            transcript = yield context.call_activity("check_transcription", transcriptionId)

            if transcript:  # Transcription completed
                # 3. Save results
                summary_result = yield context.call_activity("summarize_transcript", transcript)
                return summary_result

            # Wait 30 seconds before next check
            next_check = context.current_utc_datetime + timedelta(seconds=30)
            yield context.create_timer(next_check)

        # If we get here, transcription timed out
        raise Exception("Transcription timed out after 2 hours")

    except Exception as e:
        print(f"Exception: {str(e)}")
        return f"Error: {str(e)}"
    """ finally:
        if not context.is_replaying:
            yield context.call_activity("cleanup_storage", fileUrl) """

# Activity Functions


@app.activity_trigger(input_name="fileUrl")
def start_transcription(fileUrl: str) -> str:
    """Start transcription and return transcription ID"""
    logging.info(f"Starting transcription for fileUrl: {fileUrl}")
    transcriber = BatchTranscriber(
        subscription_key=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"]
    )

    # Start transcription
    transcriptionId = transcriber.start_transcription(
        audio_url=fileUrl,
        locale=os.environ.get("AZURE_SPEECH_LANGUAGE", "en-US")
    )

    # Update metadata
    """ storage.update_metadata(fileUrl, {
        "status": ProcessingStatus.PROCESSING,
        "transcriptionId": transcriptionId
    }) """

    return transcriptionId


@app.activity_trigger(input_name="transcriptionId")
def check_transcription(transcriptionId: str) -> str:
    """Check transcription status and return transcript if complete"""
    logging.info(f"Checking transcription: {transcriptionId}")
    transcriber = BatchTranscriber(
        subscription_key=os.environ["AZURE_SPEECH_KEY"],
        region=os.environ["AZURE_SPEECH_REGION"]
    )

    return transcriber.get_transcription_result(transcriptionId)


@app.activity_trigger(input_name="summaryResults")
def save_results(summaryResults: str) -> None:
    """Save transcription results"""
    pass


@app.activity_trigger(input_name="transcript")
def summarize_transcript(transcript: str) -> str:
    """Summarize transcript using Azure OpenAI"""
    client = AzureOpenAISummarizer(
        api_key=os.environ["AZURE_OPENAI_KEY"],
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2023-05-15"),
        deployment_name=os.environ["AZURE_MODEL_VERSION"]
    )

    logging.info(f"Summarizing transcription: {transcript}")
    return client.summarize_podcast(text=transcript).model_dump_json(indent=4)


@app.activity_trigger
def handle_error(data: dict) -> None:
    """Handle errors in the workflow"""
    pass


@app.activity_trigger(input_name="fileUrl")
def cleanup_storage(fileUrl: str):
    storage = AzureBlobStorageService(
        connection_string=os.environ["AzureWebJobsStorage"])
    storage.delete_blob_storage(container_name=fileUrl)
    return f"Cleaned up container {fileUrl}"
