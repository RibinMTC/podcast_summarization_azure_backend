import azure.functions as func
import azure.durable_functions as df
import logging
import os
import json
from datetime import datetime, timedelta

from services.chunking_service import TranscriptChunker
from services.embedding_service import AzureOpenAIEmbedding
from services.index_creation_service import AzureAISearchIndexCreationService
from services.rag_answer_generator import AzureOpenAIRagGenerator
from services.search_service import AzureAISearchService
from services.storage_service import AzureBlobStorageService
from services.batch_transcriber import BatchTranscriber
from services.rag_answer_generator import AzureOpenAIRagGenerator
from azure.core.exceptions import ResourceNotFoundError

app = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Client API - HTTP Trigger for file upload


@app.route(route="rag-test/process-audio")
@app.durable_client_input(client_name="audioProcessor")
async def upload_podcast(req: func.HttpRequest, audioProcessor: df.DurableOrchestrationClient) -> func.HttpResponse:
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
        instance_id = await audioProcessor.start_new("transcribe_and_index_orchestrator", None, {"file_url": file_url, "podcast_id": podcast_id})

        return audioProcessor.create_check_status_response(req, instance_id)
    except Exception as e:
        return {"error": str(e)}

# Client API - Http Trigger for RAG


@app.route(route="rag-test/query")
@app.durable_client_input(client_name="ragProcessor")
async def query_podcasts(req: func.HttpRequest, ragProcessor: df.DurableOrchestrationClient) -> func.HttpResponse:
    """
    Query endpoint that searches podcast transcripts using RAG
    """
    try:
        # Get query parameters
        req_body = req.get_json()
        query = req_body.get("query")
        index_name = req_body.get("index_name")

        if not query:
            return func.HttpResponse(
                json.dumps({"error": "No query provided"}),
                mimetype="application/json",
                status_code=400
            )

        # Optional filters
        filters = req_body.get("filters")

        # Start orchestration for query
        instance_id = await ragProcessor.start_new("rag_query_orchestrator", None, {"query": query, "filters": filters, "index_name": index_name})

        return ragProcessor.create_check_status_response(req, instance_id)

    except Exception as e:
        logging.error(f"Error in query: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


def get_index_name(podcast_id: str) -> str:
    return f"{podcast_id}-index"


@app.orchestration_trigger(context_name="context")
def transcribe_and_index_orchestrator(context: df.DurableOrchestrationContext):
    """
    Enhanced orchestrator function that transcribes and indexes podcast content
    """
    input_data = context.get_input()
    file_url = input_data["file_url"]
    podcast_id = input_data["podcast_id"]
    index_name = get_index_name(podcast_id)

    try:
        # 1. Start transcription and get transcription ID
        transcription_id = yield context.call_activity("start_transcription", file_url)
        if not transcription_id:
            raise Exception("Transcription could not be started")

        # 2. Poll for completion (retry every 30 seconds for up to 2 hours)
        expiry_time = context.current_utc_datetime + timedelta(hours=2)

        while context.current_utc_datetime < expiry_time:
            # Check transcription status
            transcript = yield context.call_activity("check_transcription", transcription_id)

            if transcript:  # Transcription completed
                # 3. Create search index for RAG (if it does not exist)
                yield context.call_activity("create_search_index", index_name)

                # 4. Add transcript to search index from previous step
                yield context.call_activity(
                    "index_transcript", json.dumps({"index_name": index_name, "transcript": transcript}))

                return json.dumps({"index_name": index_name})
            next_check = context.current_utc_datetime + timedelta(seconds=10)
            yield context.create_timer(next_check)
    except Exception as e:
        return {"error": str(e)}


# RAG Query Orchestrator


@app.orchestration_trigger(context_name="context")
def rag_query_orchestrator(context: df.DurableOrchestrationContext):
    """
    Orchestrator function for RAG query processing
    """
    input_data = context.get_input()
    query = input_data["query"]
    filters = input_data.get("filters")
    index_name = input_data.get("index_name")
    # Add retry to handle the case where index might not be ready yet for search.
    retry_options = df.RetryOptions(
        first_retry_interval_in_milliseconds=3000,
        max_number_of_attempts=3
    )

    try:
        # Process the RAG query
        # Pass serialized JSON string with query and filters
        query_data = json.dumps(
            {"query": query, "filters": filters, "index_name": index_name})
        answer = yield context.call_activity_with_retry("process_rag_query", retry_options, query_data)
        return answer
    except Exception as e:
        logging.error(f"Error in RAG query: {str(e)}")
        return {"error": str(e)}

# Transcription Activity Functions


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

# RAG Activity Functions


@app.activity_trigger(input_name="indexName")
async def create_search_index(indexName: str) -> str:
    """Create Azure AI Search index for podcast transcripts"""
    try:
        # Get configuration from environment variables
        search_endpoint = os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"]
        search_key = os.environ["AZURE_SEARCH_ADMIN_KEY"]

        # Check if index already exists before creating it
        search_service = AzureAISearchService(
            service_endpoint=search_endpoint,
            admin_key=search_key,
            index_name=indexName
        )

        # Try to query the index to check if it exists
        try:
            search_service.search_client.get_document_count()
            logging.info(f"Index {indexName} already exists")
            return json.dumps({"status": "exists", "indexName": indexName})
        except ResourceNotFoundError:
            # Index doesn't exist, create it
            index_service = AzureAISearchIndexCreationService(
                search_endpoint=search_endpoint,
                search_key=search_key,
                openai_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                openai_key=os.environ["AZURE_OPENAI_KEY"],
                openai_embedding_deployment=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"]
            )

            # Create index
            await index_service.create_podcast_transcript_index(indexName)

            logging.info(f"Created search index: {indexName}")
            return json.dumps({"status": "created"})

    except Exception as e:
        logging.error(f"Error creating search index: {str(e)}")
        raise


@app.activity_trigger(input_name="jsonData")
async def index_transcript(jsonData: str):
    """Index transcript for RAG using Azure AI Search"""
    try:
        data = json.loads(jsonData)
        index_name = data["index_name"]
        transcript = data["transcript"]

        # Create required services
        chunker = TranscriptChunker(
            chunk_size=int(os.environ["CHUNK_SIZE"]), chunk_overlap=int(os.environ["CHUNK_OVERLAP"]))
        embedding_service = AzureOpenAIEmbedding(
            api_key=os.environ["AZURE_OPENAI_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            deployment_name=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            embedding_model_name=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
            embedding_model_dimension=int(
                os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", 1536))
        )
        search_service = AzureAISearchService(
            service_endpoint=os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"],
            admin_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
            index_name=index_name
        )

        # 1. Chunk the transcript
        chunks = chunker.chunk_transcript(transcript)

        # 2. Generate embeddings for chunks
        embeddings = await embedding_service.generate_embeddings(texts=chunks)

        # 3. Index chunks with embeddings
        await search_service.index_transcript_chunks(
            chunks=chunks, embeddings=embeddings)
    except Exception as e:
        logging.error(f"Error indexing transcript: {str(e)}")
        raise


@app.activity_trigger(input_name="jsonData")
async def process_rag_query(jsonData: str) -> str:
    """Process RAG query and return answer with sources"""
    try:
        data = json.loads(jsonData)
        query = data["query"]
        index_name = data["index_name"]
        filters = data.get("filters")

        # Create required services
        embedding_service = AzureOpenAIEmbedding(
            api_key=os.environ["AZURE_OPENAI_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            deployment_name=os.environ["AZURE_OPENAI_EMBEDDING_DEPLOYMENT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            embedding_model_name=os.getenv(
                "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"),
            embedding_model_dimension=int(
                os.getenv("AZURE_OPENAI_EMBEDDING_DIMENSIONS", 1536))
        )
        search_service = AzureAISearchService(
            service_endpoint=os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"],
            admin_key=os.getenv("AZURE_SEARCH_ADMIN_KEY"),
            index_name=index_name
        )
        llm_service = AzureOpenAIRagGenerator(
            api_key=os.environ["AZURE_OPENAI_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ.get(
                "AZURE_OPENAI_API_VERSION", "2023-05-15"),
            deployment_name=os.environ["AZURE_MODEL_VERSION"]
        )

        # 1. Generate embedding for query
        query_embedding = (await embedding_service.generate_embeddings([query]))[0]

        # 2. Search for relevant chunks
        search_results = await search_service.search_transcripts(
            query_text=query,
            query_embedding=query_embedding,
            filters=filters,
            top=5
        )

        # 3. Format context from search results
        context = "\n\n".join([f"Podcast Excerpt {index}: {r['content']}"
                               for index, r in enumerate(search_results)])

        # 4. Generate answer using LLM with retrieved context
        prompt = f"""
        Question: {query}
        
        Podcast Transcript Excerpts:
        {context}
        """

        response = await llm_service.generate_answer(prompt)

        # 5. Return answer with sources
        return json.dumps({
            "answer": response,
            "sources": search_results
        })
    except Exception as e:
        logging.error(f"Error processing query: {str(e)}")
        raise
