from enum import Enum

from pydantic import BaseModel


class MediaType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"


class MediaIngestionResponse(BaseModel):
    message: str
    media_id: str
    file_id: str
    media_type: MediaType
    filename: str
    size_bytes: int
    transcript: str
    character_count: int
