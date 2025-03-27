import logging
from typing import Optional
from openai import AzureOpenAI


class AzureOpenAIRagGenerator:
    """Azure OpenAI Service based rag answer generation"""

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment_name: str,
        api_version: str
    ):
        """
        Initialize the Azure OpenAI Rag Answer Generator.

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

    async def generate_answer(self, prompt: str, max_length: Optional[int] = 1000) -> str:
        """
        Generate response for given prompt using Azure OpenAI.

        Args:
            prompt: Prompt to be passed to the LLM
            max_length: Maximum length of summary in tokens (default: 1000)

        Returns:
            Summarized text
        """

        try:
            # Create the prompt
            system_prompt = (
                "You are a helpful question answer assistant.\n"
                "Keep your answers concise and answer the question accurately\n"
                "Answer the following question based on the podcast transcript excerpts provided below.\n"
                "If the answer cannot be found in the transcripts, say so clearly."
            )

            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=max_length if max_length else 1000
            )
            answer = response.choices[0].message.content
            logging.info(f"Answer generation completed")

            return answer

        except Exception as e:
            logging.error(f"Error during answer generation: {e}")
            raise
