from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.models.contract import Contract
from app.models.user import User
from app.schemas.media_ingestion import MediaIngestionResponse, MediaType
from app.services.audio_transcription_service import AudioTranscriptionService
from app.services.file_ingestion_service import FileIngestionService
from app.services.video_transcription_service import VideoTranscriptionService


router = APIRouter(prefix="/ingestion", tags=["Media Ingestion"])


@router.post("/audio", response_model=MediaIngestionResponse)
async def ingest_audio(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    extension = Path(file.filename).suffix.lower()

    if extension not in AudioTranscriptionService.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio file type: {extension or 'unknown'}",
        )

    try:
        content = await file.read()

        if not content:
            raise ValueError("Uploaded audio file is empty.")

        settings = get_settings()
        max_file_size = settings.max_upload_size_mb * 1024 * 1024
        if len(content) > max_file_size:
            raise ValueError(
                f"File size exceeds the {settings.max_upload_size_mb} MB limit."
            )

        media_id = str(uuid4())
        file_id = str(uuid4())

        transcript = AudioTranscriptionService.transcribe(
            filename=file.filename,
            content=content,
        )

        FileIngestionService.save_extracted_text(
            file_id=file_id,
            extracted_text=transcript,
        )

        db.add(
            Contract(
                id=file_id,
                user_id=current_user.id,
                filename=file.filename or "unnamed",
                file_type=extension[1:],
                size_bytes=len(content),
                character_count=len(transcript),
                extracted_text_path=str(
                    FileIngestionService.EXTRACTED_DIR
                    / f"{file_id}.txt"
                ),
            )
        )
        await db.flush()

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MediaIngestionResponse(
        message="Audio received, transcribed, and added to the contract pipeline successfully.",
        media_id=media_id,
        file_id=file_id,
        media_type=MediaType.AUDIO,
        filename=file.filename,
        size_bytes=len(content),
        transcript=transcript,
        character_count=len(transcript),
    )


@router.post("/video", response_model=MediaIngestionResponse)
async def ingest_video(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    extension = Path(file.filename).suffix.lower()

    if extension not in VideoTranscriptionService.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported video file type: {extension or 'unknown'}",
        )

    try:
        content = await file.read()

        if not content:
            raise ValueError("Uploaded video file is empty.")

        media_id = str(uuid4())
        file_id = str(uuid4())

        transcript = VideoTranscriptionService.transcribe(
            filename=file.filename,
            content=content,
        )

        FileIngestionService.save_extracted_text(
            file_id=file_id,
            extracted_text=transcript,
        )

        db.add(
            Contract(
                id=file_id,
                user_id=current_user.id,
                filename=file.filename or "unnamed",
                file_type=extension[1:],
                size_bytes=len(content),
                character_count=len(transcript),
                extracted_text_path=str(
                    FileIngestionService.EXTRACTED_DIR
                    / f"{file_id}.txt"
                ),
            )
        )
        await db.flush()

    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MediaIngestionResponse(
        message="Video received, transcribed, and added to the contract pipeline successfully.",
        media_id=media_id,
        file_id=file_id,
        media_type=MediaType.VIDEO,
        filename=file.filename,
        size_bytes=len(content),
        transcript=transcript,
        character_count=len(transcript),
    )
