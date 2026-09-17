from pathlib import Path
from tempfile import NamedTemporaryFile

import whisper


class VideoTranscriptionService:

    ALLOWED_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
    }

    _model = None

    @classmethod
    def _get_model(cls):
        if cls._model is None:
            cls._model = whisper.load_model("base")

        return cls._model

    @classmethod
    def transcribe(cls, filename: str, content: bytes) -> str:

        if not filename:
            raise ValueError("Filename is required.")

        if not content:
            raise ValueError("Video content is empty.")

        extension = Path(filename).suffix.lower()

        if extension not in cls.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported video file type: {extension}"
            )

        temporary_path = None

        try:
            with NamedTemporaryFile(
                suffix=extension,
                delete=False,
            ) as temporary_file:

                temporary_file.write(content)
                temporary_path = temporary_file.name

            model = cls._get_model()

            result = model.transcribe(
                temporary_path,
                fp16=False,
            )

            text = result.get("text", "").strip()

            if not text:
                raise ValueError(
                    "No readable speech could be transcribed from the video."
                )

            return text

        except ValueError:
            raise

        except Exception as exc:
            err_msg = str(exc)
            if temporary_path and temporary_path in err_msg:
                err_msg = err_msg.replace(temporary_path, filename)
            raise ValueError(
                f"Failed to transcribe video: {err_msg}"
            ) from exc

        finally:
            if temporary_path:
                try:
                    Path(temporary_path).unlink(
                        missing_ok=True
                    )
                except OSError:
                    pass