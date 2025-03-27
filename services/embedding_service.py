import logging
from typing import List
from openai import AzureOpenAI


class AzureOpenAIEmbedding:
    def __init__(self, api_key: str, endpoint: str, deployment_name: str, api_version: str, embedding_model_name: str, embedding_model_dimension: int):
        """Initialize the embedding service with Azure OpenAI"""

        # Configure OpenAI client for Azure
        self.client = AzureOpenAI(
            azure_deployment=deployment_name,
            api_version=api_version,
            azure_endpoint=endpoint,
            api_key=api_key
        )
        self.embedding_model_name = embedding_model_name
        self.embedding_model_dimension = embedding_model_dimension

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts"""
        try:
            raw_embeddings = self.client.embeddings.create(
                input=texts, model=self.embedding_model_name, dimensions=self.embedding_model_dimension)

            # Extract embeddings from response
            embeddings = [item.embedding for item in raw_embeddings.data]
            return embeddings

        except Exception as e:
            logging.error(f"Error generating embeddings: {str(e)}")
            raise
