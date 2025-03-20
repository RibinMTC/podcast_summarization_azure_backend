# Podcast Summarizer Backend

A serverless Azure Functions application that processes podcast audio files, transcribes them using Azure Speech Services, and generates summaries using Azure OpenAI.

## Architecture

This application uses Azure Durable Functions to orchestrate a multi-step workflow:

1. Upload podcast audio file
2. Transcribe audio using Azure Speech Services
3. Summarize content using Azure OpenAI
4. Return summary and action items

## Setup and Configuration

### Prerequisites

- Python 3.12+
- Local testing: Azure Functions Core Tools and [Azurite for storage emulation](https://learn.microsoft.com/en-us/azure/azure-functions/functions-develop-local?pivots=programming-language-python#local-storage-emulator)
- Azure subscription with:
  - Azure Functions
  - Azure Storage Account
  - Azure Speech Services
  - Azure OpenAI

### Environment Variables

Create a `local.settings.json` file with the following variables:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "<storage-connection-string>",
    "AZURE_STORAGE_CONNECTION_STRING": "<storage-connection-string>",
    "AZURE_SPEECH_KEY": "<speech-service-key>",
    "AZURE_SPEECH_REGION": "<speech-service-region>",
    "AZURE_SPEECH_LANGUAGE": "en-US",
    "AZURE_OPENAI_KEY": "<openai-key>",
    "AZURE_OPENAI_ENDPOINT": "<openai-endpoint>",
    "AZURE_OPENAI_API_VERSION": "2023-05-15",
    "AZURE_MODEL_VERSION": "<deployment-name>"
  }
}
```

### Installation

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## API Endpoints

### Upload and Process Podcast

**URL**: `/api/podcast-summarizer/process-audio`
**Method**: `POST`
**Content-Type**: `multipart/form-data`

Include an audio file in the request body with the key 'file'.

**Response**: Returns a URL to check the status of the processing job.

## Development Notes

### Important Educational Notes

1. **Pydantic and OpenAI Structured Output**:
   - When using OpenAI's structured output parsing with Pydantic models, default values are not supported.
   - This is why default values were removed from the `SummaryResult` model.

2. **Azure Functions Activity Trigger Naming Conventions**:
   - Activity trigger parameter names should not include underscores.
   - Use camelCase (e.g., `fileUrl` instead of `file_url`) for parameter names.

3. **Durable Functions Workflow**:
   - The orchestrator function coordinates long-running tasks without consuming compute resources during wait periods.
   - Polling uses a timer to check transcription status, freeing up resources between checks.

4. **CORS Configuration**:
   - If you're experiencing CORS issues with a frontend, update the `host.json` file to include CORS settings:

```json
{
  "version": "2.0",
  "extensions": {
    "http": {
      "routePrefix": "api",
      "cors": {
        "allowedOrigins": ["http://localhost:3006"],
        "allowedMethods": ["GET", "POST", "OPTIONS"]
      }
    }
  }
}
```

## Key Components

- **function_app.py**: Main application file containing all function definitions
- **services/batch_transcriber.py**: Handles audio transcription using Azure Speech Services
- **services/podcast_summarizer.py**: Processes transcripts with Azure OpenAI to generate summaries
- **services/storage_service.py**: Manages file uploads to Azure Blob Storage

## Error Handling

The application includes comprehensive error handling:
- File validation
- Transcription error detection
- Timeout management for long-running transcriptions
- Error reporting in API responses
