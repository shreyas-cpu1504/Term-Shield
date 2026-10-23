import asyncio
import hashlib
import re
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import BaseModel

router = APIRouter(prefix="/tts", tags=["Text-to-Speech"])

# In-memory LRU cache for synthesized audio chunks: sha256 -> bytes
_TTS_CACHE: dict[str, bytes] = {}
_TTS_CACHE_MAX = 500

# Language code normalization for Indic & English TTS
LANG_CODE_MAP = {
    "te": "te",
    "telugu": "te",
    "te-in": "te",
    "hi": "hi",
    "hindi": "hi",
    "hi-in": "hi",
    "ta": "ta",
    "tamil": "ta",
    "ta-in": "ta",
    "kn": "kn",
    "kannada": "kn",
    "kn-in": "kn",
    "ml": "ml",
    "malayalam": "ml",
    "ml-in": "ml",
    "bn": "bn",
    "bengali": "bn",
    "bn-in": "bn",
    "mr": "mr",
    "marathi": "mr",
    "mr-in": "mr",
    "gu": "gu",
    "gujarati": "gu",
    "gu-in": "gu",
    "ur": "ur",
    "urdu": "ur",
    "ur-in": "ur",
    "en": "en",
    "english": "en",
    "en-in": "en-in",
    "en-us": "en",
}

INDIC_SCRIPT_RANGES = [
    ("te", re.compile(r"[\u0C00-\u0C7F]")),  # Telugu
    ("ta", re.compile(r"[\u0B80-\u0BFF]")),  # Tamil
    ("kn", re.compile(r"[\u0C80-\u0CFF]")),  # Kannada
    ("ml", re.compile(r"[\u0D00-\u0D7F]")),  # Malayalam
    ("bn", re.compile(r"[\u0980-\u09FF]")),  # Bengali
    ("gu", re.compile(r"[\u0A80-\u0AFF]")),  # Gujarati
    ("ur", re.compile(r"[\u0600-\u06FF]")),  # Urdu / Arabic script
    ("hi", re.compile(r"[\u0900-\u097F]")),  # Devanagari (Hindi / Marathi)
]


def detect_multilingual_language(text: str, preferred_lang: Optional[str] = None) -> str:
    """
    Detect the most appropriate language code for text-to-speech.
    If the text contains Indic script characters alongside English words,
    the Indic language is chosen so that the full sentence is spoken naturally
    instead of dropping the Indic portions.
    """
    if not text or not text.strip():
        return "en"

    norm_preferred = (preferred_lang or "").strip().lower()
    pref_code = LANG_CODE_MAP.get(norm_preferred, None)

    # Count characters matching each Indic script
    script_counts: dict[str, int] = {}
    for lang, pattern in INDIC_SCRIPT_RANGES:
        matches = pattern.findall(text)
        if matches:
            script_counts[lang] = len(matches)

    if script_counts:
        # If preferred language is one of the scripts present in text, prioritize it
        if pref_code in script_counts:
            # Distinguish Marathi from Hindi if preferred is Marathi
            if pref_code == "mr" and "hi" in script_counts:
                return "mr"
            return pref_code

        if pref_code == "mr" and "hi" in script_counts:
            return "mr"

        # Otherwise pick the script with the highest count
        best_lang = max(script_counts.items(), key=lambda item: item[1])[0]
        return best_lang

    # No Indic characters detected; use preferred language if valid or default to English
    if pref_code and pref_code in ("en", "en-in"):
        return pref_code

    return "en"


def _split_text_into_tts_chunks(text: str, max_chars: int = 170) -> list[str]:
    """
    Split text into natural chunks for TTS API without cutting words or sentences.
    """
    # Clean text from markdown formatting
    cleaned = re.sub(r"[*_#`~\[\]()<>{}|\\]", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        return []

    if len(cleaned) <= max_chars:
        return [cleaned]

    # Split by sentence terminators first (. ! ? \n | full stops in Indic scripts)
    sentence_delimiters = re.compile(r"(?<=[.!?।॥])\s+")
    sentences = sentence_delimiters.split(cleaned)

    chunks: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if len(sentence) > max_chars:
            # Split sentence by commas, semicolons, or words
            sub_parts = re.split(r"(?<=[,;:])\s+", sentence)
            for part in sub_parts:
                part = part.strip()
                if not part:
                    continue
                if len(part) > max_chars:
                    # Break by words
                    words = part.split(" ")
                    sub_chunk = ""
                    for word in words:
                        if len(sub_chunk) + len(word) + 1 <= max_chars:
                            sub_chunk = f"{sub_chunk} {word}".strip()
                        else:
                            if sub_chunk:
                                chunks.append(sub_chunk)
                            sub_chunk = word
                    if sub_chunk:
                        chunks.append(sub_chunk)
                else:
                    if len(current_chunk) + len(part) + 1 <= max_chars:
                        current_chunk = f"{current_chunk} {part}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = part
        else:
            if len(current_chunk) + len(sentence) + 1 <= max_chars:
                current_chunk = f"{current_chunk} {sentence}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = sentence

    if current_chunk:
        chunks.append(current_chunk)

    return [c for c in chunks if c.strip()]


async def _synthesize_audio_stream(text: str, lang: str) -> bytes:
    """
    Synthesize audio using Google Translate TTS service, chunking text
    and concatenating MP3 frames into a single seamless audio stream.
    """
    chunks = _split_text_into_tts_chunks(text, max_chars=180)
    if not chunks:
        return b""

    cache_key = hashlib.sha256(f"{lang}:{text}".encode("utf-8")).hexdigest()
    if cache_key in _TTS_CACHE:
        return _TTS_CACHE[cache_key]

    audio_frames = bytearray()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://translate.google.com/",
    }

    async with httpx.AsyncClient(timeout=12.0) as client:
        for chunk in chunks:
            params = {
                "ie": "UTF-8",
                "q": chunk,
                "tl": lang,
                "client": "tw-ob",
            }
            try:
                response = await client.get(
                    "https://translate.google.com/translate_tts",
                    params=params,
                    headers=headers,
                )
                if response.status_code == 200 and len(response.content) > 0:
                    audio_frames.extend(response.content)
            except Exception as exc:
                # If a chunk fails, continue trying subsequent chunks
                continue

    audio_bytes = bytes(audio_frames)
    if audio_bytes:
        if len(_TTS_CACHE) >= _TTS_CACHE_MAX:
            _TTS_CACHE.pop(next(iter(_TTS_CACHE)))
        _TTS_CACHE[cache_key] = audio_bytes

    return audio_bytes


class TTSRequest(BaseModel):
    text: str
    lang: Optional[str] = None
    preferred_lang: Optional[str] = None


@router.get("")
async def get_tts_audio(
    text: str = Query(..., description="Text to synthesize to speech"),
    lang: Optional[str] = Query(None, description="Target language code or auto"),
    preferred_lang: Optional[str] = Query(None, description="User language preference"),
):
    """
    Stream high-fidelity multilingual speech audio.
    Supports Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali, Marathi, Gujarati, Urdu, and English,
    including mixed-language sentences containing English legal terminology inside Indic sentences.
    """
    if not text or not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text parameter must not be empty",
        )

    # Determine optimal speech language
    target_lang = lang if (lang and lang != "auto") else None
    if not target_lang:
        target_lang = detect_multilingual_language(text, preferred_lang)

    target_lang = LANG_CODE_MAP.get(target_lang.lower(), target_lang)

    audio_bytes = await _synthesize_audio_stream(text, target_lang)

    if not audio_bytes:
        # Fallback to English if primary language synthesis had no output
        if target_lang != "en":
            audio_bytes = await _synthesize_audio_stream(text, "en")

    if not audio_bytes:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Unable to synthesize audio for the provided text",
        )

    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Type": "audio/mpeg",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",
            "X-TTS-Language": target_lang,
        },
    )


@router.post("")
async def post_tts_audio(payload: TTSRequest):
    """
    POST variant for longer text bodies.
    """
    return await get_tts_audio(
        text=payload.text,
        lang=payload.lang,
        preferred_lang=payload.preferred_lang,
    )
