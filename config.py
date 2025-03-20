from dataclasses import dataclass


@dataclass
class Config:
    """Application configuration."""

    # Azure Storage
    blob_connection_string: str
    podcasts_container_name: str = "podcasts"

    # Audio download settings
    audio_format: str = "mp3"
    audio_quality: str = "192"
    download_timeout: int = 300  # seconds
