from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.models.contract import Contract
from app.models.user import User
from app.schemas.file_ingestion import (
    FileIngestionResponse,
    FileType,
)
from app.services.file_ingestion_service import FileIngestionService
from app.services.text_extraction_service import TextExtractionService
from app.services.url_ingestion_service import URLIngestionService


router = APIRouter(
    prefix="/ingestion",
    tags=["Ingestion"],
)


class URLIngestionRequest(BaseModel):
    url: HttpUrl


@router.post(
    "/file",
    response_model=FileIngestionResponse,
)
async def ingest_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileIngestionResponse:

    try:
        file_id, content = await FileIngestionService.read_file(
            file
        )

        extracted_text = TextExtractionService.extract(
            filename=file.filename,
            content=content,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="No readable text could be extracted from the file.",
        )

    FileIngestionService.save_extracted_text(
        file_id=file_id,
        extracted_text=extracted_text,
    )

    extension = Path(file.filename).suffix.lower()

    db.add(
        Contract(
            id=file_id,
            user_id=current_user.id,
            filename=file.filename or "unnamed",
            file_type=extension[1:],
            size_bytes=len(content),
            character_count=len(extracted_text),
            extracted_text_path=str(
                FileIngestionService.EXTRACTED_DIR
                / f"{file_id}.txt"
            ),
        )
    )
    await db.flush()

    return FileIngestionResponse(
        message="File received and text extracted successfully.",
        file_id=file_id,
        file_type=FileType(extension[1:]),
        filename=file.filename,
        size_bytes=len(content),
        extracted_text=extracted_text,
        character_count=len(extracted_text),
    )


@router.post(
    "/url",
    response_model=FileIngestionResponse,
)
async def ingest_url(
    request: URLIngestionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FileIngestionResponse:

    try:
        filename, content = await URLIngestionService.download(
            str(request.url)
        )

        extension = Path(filename).suffix.lower()

        extracted_text = TextExtractionService.extract(
            filename=filename,
            content=content,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not extracted_text:
        raise HTTPException(
            status_code=400,
            detail="No readable text could be extracted from the URL.",
        )

    file_id = str(uuid4())

    FileIngestionService.UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    stored_filename = f"{file_id}{extension}"

    stored_path = (
        FileIngestionService.UPLOAD_DIR
        / stored_filename
    )

    stored_path.write_bytes(content)

    FileIngestionService.save_extracted_text(
        file_id=file_id,
        extracted_text=extracted_text,
    )

    db.add(
        Contract(
            id=file_id,
            user_id=current_user.id,
            filename=filename,
            file_type=extension[1:],
            size_bytes=len(content),
            character_count=len(extracted_text),
            extracted_text_path=str(
                FileIngestionService.EXTRACTED_DIR
                / f"{file_id}.txt"
            ),
        )
    )
    await db.flush()

    return FileIngestionResponse(
        message="Contract URL received and text extracted successfully.",
        file_id=file_id,
        file_type=FileType(extension[1:]),
        filename=filename,
        size_bytes=len(content),
        extracted_text=extracted_text,
        character_count=len(extracted_text),
    )