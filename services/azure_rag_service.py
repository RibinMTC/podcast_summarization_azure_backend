import os
import logging
from typing import List, Dict, Any, Optional
import json

from .embedding_service import AzureOpenAIEmbedding
from .chunking_service import TranscriptChunker
from .search_service import AzureAISearchService
from .podcast_summarizer import AzureOpenAISummarizer


class PodcastRAGService:
    def __init__(self):
        """Initialize the RAG service orchestrator"""
        self.chunker = TranscriptChunker()
        self.embedding_service = AzureOpenAIEmbedding()
        self.search_service = AzureAISearchService()
        self.llm_service = AzureOpenAISummarizer(
            api_key=os.environ["AZURE_OPENAI_KEY"],
            endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            api_version=os.environ.get(
                "AZURE_OPENAI_API_VERSION", "2023-05-15"),
            deployment_name=os.environ["AZURE_MODEL_VERSION"]
        )

    async def process_and_index_transcript(self, podcast_id: str, transcript: str) -> None:
        """Process a transcript and index it for RAG"""
        # 1. Chunk the transcript
        chunks = self.chunker.chunk_transcript(transcript)

        # 2. Generate embeddings for chunks
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = await self.embedding_service.generate_embeddings(chunk_texts)

        # 3. Index chunks with embeddings
        await self.search_service.index_transcript_chunks(podcast_id, chunks, embeddings)

        return {
            "indexed_chunks": len(chunks),
            "podcast_id": podcast_id
        }

    async def answer_query(self, query: str, filters: Optional[str] = None) -> Dict[str, Any]:
        """Process a RAG query and return answer with sources"""
        # 1. Generate embedding for query
        query_embedding = await self.embedding_service.generate_embeddings([query])

        # 2. Search for relevant chunks
        search_results = await self.search_service.search_transcripts(
            query_text=query,
            query_embedding=query_embedding[0],
            filters=filters,
            top=5
        )

        # 3. Format context from search results
        context = "\n\n".join([f"[Podcast {r['podcast_id']} at {r['timestamp'] or 'unknown time'}]: {r['text']}"
                              for r in search_results])

        # 4. Generate answer using LLM with retrieved context
        prompt = f"""
        Answer the following question based on the podcast transcript excerpts provided below.
        If the answer cannot be found in the transcripts, say so clearly.
        
        Question: {query}
        
        Podcast Transcript Excerpts:
        {context}
        """

        response = await self.llm_service.generate_answer(prompt)

        # 5. Return answer with sources
        return {
            "answer": response,
            "sources": search_results
        }
