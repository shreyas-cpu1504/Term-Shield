from enum import Enum

from pydantic import BaseModel, Field


class InputType(str, Enum):
    TEXT = "text"
    DOCUMENT = "document"
    IMAGE = "image"
    URL = "url"
    AUDIO = "audio"
    VIDEO = "video"


class TextIngestionRequest(BaseModel):
    input_type: InputType = InputType.TEXT
    content: str = Field(
        min_length=1,
        max_length=100_000,
        description="Text content to be analyzed.",
    )


class IngestionResponse(BaseModel):
    message: str
    input_type: InputType
    character_count: int
