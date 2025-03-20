import logging
from typing import List, Protocol, Optional

from openai import AzureOpenAI
from pydantic import BaseModel, Field


class SummaryResult(BaseModel):
    """Pydantic model for summarization results."""
    # Note: Default values have been removed, since they are not supported when using structured output for chat completion.
    summary: str = Field(
        description="Concise summary of the podcast")
    action_items: List[str] = Field(
        description="List of actionable items from the podcast")


class SummarizerInterface(Protocol):
    """Protocol for text summarization services."""

    def summarize_podcast(self, text: str, max_length: Optional[int] = None) -> SummaryResult:
        """
        Summarize text content.

        Args:
            text: Text content to summarize
            max_length: Maximum length of summary in tokens (optional)

        Returns:
            SummaryResult object containing summary and action_item
        """
        ...


class AzureOpenAISummarizer:
    """Azure OpenAI Service based summarizer implementation."""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment_name: str,
        api_version: str
    ):
        """
        Initialize the Azure OpenAI summarizer.

        Args:
            api_key: Azure OpenAI API key
            endpoint: Azure OpenAI endpoint URL
            deployment_name: Deployment name for the model
            api_version: API version to use
        """
        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version
        )
        self.deployment_name = deployment_name

    def summarize_podcast(self, text: str, max_length: Optional[int] = 1000) -> SummaryResult:
        """
        Summarize text using Azure OpenAI.

        Args:
            text: Text to summarize
            max_length: Maximum length of summary in tokens (default: 1000)

        Returns:
            Summarized text
        """
        logging.info(f"Starting summarization of {len(text)} characters")

        try:
            # Create the prompt
            system_prompt = (
                "You are a helpful podcast summarization assistant. "
                "Analyze the following podcast transcript and provide TWO separate sections:\n"
                "1. SUMMARY: A concise summary including key topics, main ideas, and important takeaways.\n"
                "2. ACTION_ITEMS: A bulleted list of actionable items that listeners might want to implement "
                "based on the podcast content.\n\n"
                "Format your response as a JSON object with two keys: 'summary' and 'action_items'."
            )

            response = self.client.beta.chat.completions.parse(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.7,
                max_tokens=max_length if max_length else 1000,
                response_format=SummaryResult
            )
            summary_result = response.choices[0].message.parsed
            logging.info(f"Summarization completed")

            return summary_result

        except Exception as e:
            logging.error(f"Error during summarization: {e}")
            raise
