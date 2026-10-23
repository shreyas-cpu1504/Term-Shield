from dataclasses import dataclass

from app.schemas.ingestion import InputType


@dataclass(frozen=True)
class NormalizedInput:
    input_type: InputType
    content: str
    character_count: int


class IngestionService:

    @staticmethod
    def process_text(
        input_type: InputType,
        content: str,
    ) -> NormalizedInput:
        cleaned_content = content.strip()

        return NormalizedInput(
            input_type=input_type,
            content=cleaned_content,
            character_count=len(cleaned_content),
        )
