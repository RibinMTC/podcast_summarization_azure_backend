import logging
from typing import List, Dict, Any, Optional
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery


class AzureAISearchService:
    def __init__(self, service_endpoint: str, admin_key: str, index_name: str):
        """Initialize Azure AI Search service"""

        # Create search client
        self.search_client = SearchClient(
            endpoint=service_endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(admin_key)
        )

    async def index_transcript_chunks(self, chunks: List[str],
                                      embeddings: List[List[float]]):
        """Index transcript chunks with their embeddings"""
        try:
            documents = []

            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_id = f"chunk-{i}"

                document = {
                    "id": doc_id,
                    "content": chunk,
                    "contentVector": embedding
                }

                documents.append(document)

            self.search_client.upload_documents(documents=documents)

            logging.info(
                f"Indexed {len(documents)} chunks.")

        except Exception as e:
            logging.error(f"Error indexing transcript chunks: {str(e)}")
            raise

    async def search_transcripts(self, query_text: str, query_embedding: List[float],
                                 filters: Optional[str] = None, top: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant transcript chunks using hybrid search"""
        try:
            vector_query = VectorizedQuery(
                vector=query_embedding, k_nearest_neighbors=50, fields="contentVector")

            # Execute search with both keyword and vector components
            results = self.search_client.search(
                search_text=query_text,
                vector_queries=[vector_query],
                filter=filters,
                top=top,
                select=["content"]
            )

            # Process results
            search_results = []
            for result in results:
                search_results.append({
                    "content": result["content"],
                    "score": result["@search.score"]
                })

            return search_results

        except Exception as e:
            logging.error(f"Error searching transcripts: {str(e)}")
            raise
