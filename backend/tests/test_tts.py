import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.tts import detect_multilingual_language, _split_text_into_tts_chunks
from app.main import app


def test_detect_multilingual_language_telugu():
    text = "ఈ Agreement ప్రకారం payment 30 రోజుల్లో చేయాలి."
    lang = detect_multilingual_language(text)
    assert lang == "te"


def test_detect_multilingual_language_tamil():
    text = "இந்த agreement-ல் payment 30 days లోపు చేయాలి."
    # Tamil has 16 Tamil characters vs 9 Telugu characters
    lang = detect_multilingual_language(text, preferred_lang="Tamil")
    assert lang == "ta"


def test_detect_multilingual_language_pure_indic():
    assert detect_multilingual_language("నమస్కారం") == "te"
    assert detect_multilingual_language("नमस्ते आप कैसे हैं") == "hi"
    assert detect_multilingual_language("வணக்கம்") == "ta"
    assert detect_multilingual_language("নমস্কার") == "bn"
    assert detect_multilingual_language("નમસ્તે") == "gu"
    assert detect_multilingual_language("ನಮಸ್ಕಾರ") == "kn"
    assert detect_multilingual_language("നമസ്കാരം") == "ml"


def test_detect_multilingual_language_marathi_preference():
    text = "हा करार दोन्ही पक्षांसाठी बंधनकारक आहे."
    lang = detect_multilingual_language(text, preferred_lang="Marathi")
    assert lang == "mr"


def test_detect_multilingual_language_english():
    text = "This contract shall terminate upon thirty days written notice."
    lang = detect_multilingual_language(text)
    assert lang in ("en", "en-in")


def test_split_text_into_tts_chunks():
    short_text = "Short text"
    chunks = _split_text_into_tts_chunks(short_text, max_chars=50)
    assert chunks == ["Short text"]

    long_text = (
        "Clause 4 Termination. Either party may terminate this agreement with 30 days written notice. "
        "Upon termination, all outstanding payments must be settled immediately without any delay. "
        "Any disputes arising from this termination shall be resolved through binding arbitration."
    )
    chunks = _split_text_into_tts_chunks(long_text, max_chars=80)
    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 85
        assert len(chunk.strip()) > 0


@pytest.mark.asyncio
async def test_tts_endpoint_get_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/tts",
            params={
                "text": "ఈ Agreement ప్రకారం payment 30 రోజుల్లో చేయాలి.",
                "preferred_lang": "Telugu",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "audio/mpeg"
        assert len(response.content) > 0
        assert response.headers.get("X-TTS-Language") == "te"


@pytest.mark.asyncio
async def test_tts_endpoint_post_success():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/tts",
            json={
                "text": "Payment shall be made within 30 days.",
                "lang": "en",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("content-type") == "audio/mpeg"
        assert len(response.content) > 0


@pytest.mark.asyncio
async def test_tts_endpoint_empty_text():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/tts",
            params={"text": "   "},
        )
        assert response.status_code == 400
