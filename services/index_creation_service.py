import logging
from typing import List
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
    SearchIndex
)


class AzureAISearchIndexCreationService:
    """Service for creating and managing Azure AI Search indexes with vector and semantic search capabilities."""

    def __init__(
        self,
        search_endpoint: str,
        search_key: str,
        openai_endpoint: str,
        openai_key: str,
        openai_embedding_deployment: str,
        openai_embedding_dimensions: int = 1536,
        embedding_model_name: str = "text-embedding-3-small"
    ):
        """
        Initialize the Search Index Service.

        Args:
            search_endpoint: Azure AI Search service endpoint
            search_key: Azure AI Search admin key
            openai_endpoint: Azure OpenAI service endpoint
            openai_key: Azure OpenAI API key
            openai_embedding_deployment: Azure OpenAI embedding model deployment name
            openai_embedding_dimensions: Dimensions of embedding vectors
            embedding_model_name: Name of the embedding model
        """
        # Create credentials and client
        self.credential = AzureKeyCredential(search_key)
        self.index_client = SearchIndexClient(
            endpoint=search_endpoint, credential=self.credential)

        # Store only what's needed across multiple methods
        self.openai_endpoint = openai_endpoint
        self.openai_key = openai_key
        self.openai_embedding_deployment = openai_embedding_deployment
        self.embedding_dimensions = openai_embedding_dimensions
        self.embedding_model_name = embedding_model_name

    async def create_podcast_transcript_index(self, index_name: str = "podcast-transcripts"):
        """
        Create a search index for podcast transcripts with vector search and semantic search capabilities.

        Args:
            index_name: Name of the search index to create

        Returns:
            The created SearchIndex
        """
        # Define algorithm configuration names
        algorithm_config_name = "podcastTranscriptionHnsw"
        vectorizer_name = "podcastTranscriptionOpenAI"
        vector_search_profile_name = "podcastTranscriptionHnswProfile"
        semantic_config_name = "podcast-transcription-semantic-config"

        # Create components
        fields = self._create_fields(vector_search_profile_name)
        vector_search = self._create_vector_search(
            algorithm_config_name, vectorizer_name, vector_search_profile_name)
        semantic_search = self._create_semantic_search(semantic_config_name)

        # Create the search index
        self._create_index(index_name, fields, vector_search, semantic_search)

    def _create_fields(self, vector_search_profile_name: str) -> List[SearchField]:
        """
        Create the fields for the podcast transcript index.

        Args:
            vector_search_profile_name: Name of the vector search profile to use

        Returns:
            List of SearchField objects
        """
        return [
            SearchField(
                name="id",
                type=SearchFieldDataType.String,
                sortable=True,
                filterable=True,
                facetable=True,
                key=True
            ),
            SearchField(
                name="content",
                type=SearchFieldDataType.String,
                sortable=False,
                filterable=False,
                facetable=False
            ),
            SearchField(
                name="contentVector",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.Single),
                vector_search_dimensions=self.embedding_dimensions,
                vector_search_profile_name=vector_search_profile_name
            ),
        ]

    def _create_vector_search(self, algorithm_name: str, vectorizer_name: str, profile_name: str) -> VectorSearch:
        """
        Create the vector search configuration.

        Args:
            algorithm_name: Name of the algorithm configuration
            vectorizer_name: Name of the vectorizer
            profile_name: Name of the vector search profile

        Returns:
            VectorSearch configuration
        """
        return VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(name=algorithm_name),
            ],
            vectorizers=[
                AzureOpenAIVectorizer(
                    vectorizer_name=vectorizer_name,
                    kind="azureOpenAI",
                    parameters=AzureOpenAIVectorizerParameters(
                        resource_url=self.openai_endpoint,
                        deployment_name=self.openai_embedding_deployment,
                        model_name=self.embedding_model_name,
                        api_key=self.openai_key,
                    ),
                ),
            ],
            profiles=[
                VectorSearchProfile(
                    name=profile_name,
                    algorithm_configuration_name=algorithm_name,
                    vectorizer_name=vectorizer_name,
                )
            ],
        )

    def _create_semantic_search(self, config_name: str) -> SemanticSearch:
        """
        Create the semantic search configuration.

        Args:
            config_name: Name of the semantic configuration

        Returns:
            SemanticSearch configuration
        """
        semantic_config = SemanticConfiguration(
            name=config_name,
            prioritized_fields=SemanticPrioritizedFields(
                content_fields=[SemanticField(field_name="content")]
            ),
        )

        return SemanticSearch(configurations=[semantic_config])

    def _create_index(self, index_name: str, fields: List[SearchField],
                      vector_search: VectorSearch, semantic_search: SemanticSearch):
        """
        Create the search index with the provided components.

        Args:
            index_name: Name of the search index
            fields: List of SearchField objects
            vector_search: VectorSearch configuration
            semantic_search: SemanticSearch configuration

        Returns:
            Created SearchIndex
        """
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )

        try:
            result = self.index_client.create_or_update_index(index)
            logging.info(f"Search index '{result.name}' created successfully")
        except Exception as e:
            logging.error(f"Error creating search index: {str(e)}")
            raise

    def delete_index(self, index_name: str) -> None:
        """
        Delete a search index.

        Args:
            index_name: Name of the index to delete
        """
        try:
            self.index_client.delete_index(index_name)
            logging.info(f"Search index '{index_name}' deleted successfully")
        except Exception as e:
            logging.error(f"Error deleting search index: {str(e)}")
            raise

    def list_indexes(self):
        """List all indexes in the search service."""
        return list(self.index_client.list_indexes())
