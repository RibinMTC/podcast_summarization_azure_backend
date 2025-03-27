from typing import List
import semchunk
import tiktoken


class TranscriptChunker:
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        """Initialize the chunking service"""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = semchunk.chunkerify(
            tiktoken.encoding_for_model('gpt-4'), chunk_size)

    def chunk_transcript(self, transcript: str) -> List[str]:
        """
        Split transcript into overlapping chunks for better RAG processing
        Returns a list of chunk objects with text and metadata
        """
        if not transcript:
            return []

        # Simple chunking by character count with overlap
        chunks = self.chunker(transcript, overlap=self.chunk_overlap)

        return chunks
