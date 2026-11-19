import json
from decimal import Decimal

import httpx
import pytest

from app.infrastructure.ai.openai_vision import OpenAIVisionRecognizer, build_vision_payload
from app.services.recognition import (
    RecognitionEmpty,
    RecognitionInvalid,
    RecognitionTimeout,
    RecognitionUnavailable,
    load_json_object,
    parse_recognition_payload,
)


def test_parse_accepts_documented_shape_and_drops_invalid_items():
    payload = {
        "items": [
            {"name": "Cooked rice", "estimated_weight_g": 150, "recognition_note": "Estimated from visible portion"},
            {"name": "Chicken breast", "estimated_weight_g": 120, "recognition_note": "Estimated"},
            {"name": "", "estimated_weight_g": 100},
            {"name": "Слишком много", "estimated_weight_g": 9000},
            {"name": "Флаг", "estimated_weight_g": True},
        ]
    }
    items = parse_recognition_payload(payload)
    assert [item.name for item in items] == ["Cooked rice", "Chicken breast"]
    assert items[0].estimated_weight_g == Decimal("150.0")


def test_parse_empty_and_invalid_payloads():
    with pytest.raises(RecognitionEmpty):
        parse_recognition_payload({"items": []})
    with pytest.raises(RecognitionInvalid):
        parse_recognition_payload({"items": [{"name": "x", "estimated_weight_g": -1}]})
    with pytest.raises(RecognitionInvalid):
        parse_recognition_payload({"food": []})


def test_load_json_object_strips_fences():
    data = load_json_object('```json\n{"items": []}\n```')
    assert data == {"items": []}


def test_payload_puts_image_in_body_and_not_the_api_key():
    payload = build_vision_payload(
        model="gpt-4o-mini",
        image=b"image-bytes",
        mime_type="image/jpeg",
        user_text="это плов",
        json_mode=True,
    )
    encoded = json.dumps(payload)
    assert "secret-key" not in encoded
    assert "data:image/jpeg;base64," in encoded
    assert payload["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_openai_recognizer_parses_success_and_maps_errors():
    def ok(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {"items": [{"name": "Рис", "estimated_weight_g": 100, "recognition_note": "порция"}]}
                            )
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(ok)) as client:
        recognizer = OpenAIVisionRecognizer(
            api_key="secret",
            base_url="https://example.test/v1",
            model="gpt-4o-mini",
            json_mode=True,
            client=client,
        )
        items = await recognizer.recognize(b"img", "image/jpeg", None)
    assert items[0].name == "Рис"
    assert items[0].estimated_weight_g == Decimal("100.0")

    def timeout(request: httpx.Request) -> httpx.Response:
        del request
        raise httpx.TimeoutException("slow")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as client:
        recognizer.client = client
        with pytest.raises(RecognitionTimeout):
            await recognizer.recognize(b"img", "image/jpeg", None)

    def broken(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(broken)) as client:
        recognizer.client = client
        with pytest.raises(RecognitionInvalid):
            await recognizer.recognize(b"img", "image/jpeg", None)

    def unavailable(request: httpx.Request) -> httpx.Response:
        del request
        return httpx.Response(503, json={"error": "down"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(unavailable)) as client:
        recognizer.client = client
        with pytest.raises(RecognitionUnavailable):
            await recognizer.recognize(b"img", "image/jpeg", None)
