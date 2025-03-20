import requests
from typing import Optional


class BatchTranscriber:
    """Service for handling batch transcription using Azure Speech Service REST API"""

    def __init__(self, subscription_key: str, region: str):
        self.subscription_key = subscription_key
        self.region = region
        self.base_url = f"https://{region}.api.cognitive.microsoft.com/speechtotext/v3.2"

    def start_transcription(self, audio_url: str, locale: str = "en-US") -> str:
        """
        Start a batch transcription job
        Returns the transcription ID
        """
        url = f"{self.base_url}/transcriptions"

        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json"
        }
        # The url has to have authorization to be accessed (which is provided by sas url from blob storage)
        body = {
            "contentUrls": [audio_url],
            "locale": locale,
            "displayName": "test podcast transcription"
        }

        try:
            response = requests.post(url, headers=headers, json=body)
            # Print the response for debugging
            print(f"Response Status: {response.status_code}")
            print(f"Response Text: {response.text}")
            response.raise_for_status()

            # Get the transcription ID from the response
            transcription_id = response.json().get("self", "").split("/")[-1]
            return transcription_id
        except requests.exceptions.RequestException as e:
            print(f"Error starting transcription: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"Error response: {e.response.text}")
            raise

    def get_transcription_status(self, transcription_id: str) -> dict:
        """Get the status of a transcription job"""
        url = f"{self.base_url}/transcriptions/{transcription_id}"

        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_transcription_result(self, transcription_id: str) -> Optional[str]:
        """
        Get the transcription result if available
        Returns None if not yet completed
        """
        status = self.get_transcription_status(transcription_id)
        if status.get("status") == "Failed":
            raise Exception(
                f"Transcription failed: {status.get('properties').get('error').get('message')}")

        if status.get("status") != "Succeeded":
            return None

        # Get the results URL
        files = status.get("links", {}).get("files")
        if not files:
            return None

        # Get the results file
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key
        }

        response = requests.get(files, headers=headers)
        response.raise_for_status()

        # Get the first results file URL
        results_files = response.json().get("values", [])
        if not results_files:
            return None

        result_url = results_files[0].get("links", {}).get("contentUrl")
        if not result_url:
            return None

        # Get the actual transcription
        response = requests.get(result_url)
        response.raise_for_status()

        # Extract combined recognized text
        result = response.json()
        combined_text = []

        for segment in result.get("combinedRecognizedPhrases", []):
            combined_text.append(segment.get("display", ""))

        return "\n".join(combined_text)

    def delete_transcription(self, transcription_id: str) -> None:
        """Delete a transcription job and its results"""
        url = f"{self.base_url}/transcriptions/{transcription_id}"

        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key
        }

        response = requests.delete(url, headers=headers)
        response.raise_for_status()


class MockBatchTranscriber:
    """Mock Service for handling batch transcription using Azure Speech Service REST API"""

    def start_transcription(self, audio_url: str, locale: str = "en-US") -> str:
        """
        Mock start a batch transcription job
        Returns the transcription ID
        """
        # Get the transcription ID from the response
        transcription_id = "mock_transcription_id"
        return transcription_id

    def get_transcription_result(self, transcription_id: str) -> Optional[str]:
        """
        Mock get the transcription result if available
        Returns None if not yet completed
        """

        return "This is a mock transcription for testing."

    def delete_transcription(self, transcription_id: str) -> None:
        """Delete a transcription job and its results"""
        print("Deleted transcription")
