import os
from pathlib import Path

from google import genai

from app.core.config import get_settings


class GeminiService:

    @classmethod
    def _load_api_key(cls) -> str:
        settings = get_settings()
        if settings.gemini_api_key:
            return settings.gemini_api_key.strip()

        env_val = os.environ.get("GEMINI_API_KEY")
        if env_val:
            return env_val.strip()

        base_dir = Path(__file__).resolve().parent.parent.parent
        env_candidates = [base_dir / ".env", Path(".env")]

        for env_path in env_candidates:
            if env_path.exists():
                try:
                    for line in env_path.read_text(encoding="utf-8-sig").splitlines():
                        if "=" not in line:
                            continue
                        name, value = line.split("=", 1)
                        if name.strip().lstrip("\ufeff") == "GEMINI_API_KEY":
                            value = value.strip()
                            if value:
                                return value
                except Exception:
                    pass

        raise RuntimeError(
            "GEMINI_API_KEY is not configured in settings, environment, or .env."
        )

    @classmethod
    def _load_model(cls) -> str:
        settings = get_settings()
        if getattr(settings, "gemini_model", None):
            return settings.gemini_model.strip()

        env_val = os.environ.get("GEMINI_MODEL")
        if env_val and env_val.strip():
            return env_val.strip()

        return "gemini-flash-lite-latest"

    @classmethod
    def generate(cls, prompt: str) -> str:
        api_key = cls._load_api_key()
        primary_model = cls._load_model()

        client = genai.Client(
            api_key=api_key,
            http_options={
                "timeout": 30000
            },
        )

        models_to_try = [primary_model]
        if primary_model != "gemini-flash-lite-latest":
            models_to_try.append("gemini-flash-lite-latest")

        last_error = None
        for model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                text = getattr(response, "text", None)
                if text and text.strip():
                    return text.strip()
            except Exception as e:
                last_error = e
                # Only retry with fallback model if it was a rate-limit/quota error
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    continue
                raise e

        if last_error:
            raise last_error

        raise RuntimeError(
            "Gemini returned an empty response."
        )