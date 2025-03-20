from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    NOT_FOUND = "not_found"
    ERROR = "error"


@dataclass
class PodcastMetadata:
    id: str
    original_filename: str
    upload_time: datetime
    status: ProcessingStatus
    error_message: str = None