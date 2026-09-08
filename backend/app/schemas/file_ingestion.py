from enum import Enum

from pydantic import BaseModel


class FileType(str, Enum):
    TXT = "txt"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"


class FileIngestionResponse(BaseModel):
    message: str
    file_id: str
    file_type: FileType
    filename: str
    size_bytes: int
    extracted_text: str
    character_count: int
