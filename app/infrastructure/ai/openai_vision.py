import base64
import logging

import httpx

logger = logging.getLogger(__name__)

from app.services.recognition import (
    FoodRecognizer,
    RecognitionInvalid,
    RecognitionTimeout,
    RecognitionUnavailable,
    RecognizedItem,
    load_json_object,
    parse_recognition_payload,
)

SYSTEM_PROMPT = """Ты оцениваешь еду на фотографии для дневника питания.
Это приблизительная оценка видимой порции, не измерение и не лабораторный анализ.
Верни только JSON вида:
{"items":[{"name":"короткое название на русском","estimated_weight_g":150,"recognition_note":"кратко, почему такой вес"}]}
Правила:
- включай только видимую еду и напитки
- estimated_weight_g — число граммов съедобной порции от 1 до 3000
- если еды не видно, верни {"items":[]}
- не пиши калории и не добавляй текст вне JSON
"""


def build_vision_payload(
    *,
    model: str,
    image: bytes,
    mime_type: str,
    user_text: str | None,
    json_mode: bool,
) -> dict:
    instruction = "Оцени продукты на фото."
    if user_text:
        instruction = (
            f"Комментарий пользователя: {user_text}\n"
            "Учти комментарий только если он не противоречит тому, что видно на фото."
        )
    encoded = base64.b64encode(image).decode("ascii")
    payload: dict = {
        "model": model,
        "temperature": 0,
        "max_tokens": 1500,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": instruction},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{encoded}"},
                    },
                ],
            },
        ],
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    return payload


def message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    raise RecognitionInvalid("empty model content")


class OpenAIVisionRecognizer:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        json_mode: bool,
        client: httpx.AsyncClient,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.json_mode = json_mode
        self.client = client

    async def recognize(
        self,
        image: bytes,
        mime_type: str,
        user_text: str | None,
    ) -> list[RecognizedItem]:
        payload = build_vision_payload(
            model=self.model,
            image=image,
            mime_type=mime_type,
            user_text=user_text,
            json_mode=self.json_mode,
        )
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
        except httpx.TimeoutException:
            raise RecognitionTimeout() from None
        except httpx.HTTPError:
            raise RecognitionUnavailable() from None
        if response.status_code >= 400:
            logger.warning("vision provider status=%s", response.status_code)
            raise RecognitionUnavailable(str(response.status_code))
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise RecognitionInvalid("unexpected provider payload") from None
        return parse_recognition_payload(load_json_object(message_text(content)))


def build_recognizer(
    *,
    api_key: str,
    base_url: str,
    model: str,
    json_mode: bool,
    client: httpx.AsyncClient | None,
) -> FoodRecognizer:
    if not api_key.strip() or client is None:
        return UnconfiguredRecognizer()
    return OpenAIVisionRecognizer(
        api_key=api_key,
        base_url=base_url,
        model=model,
        json_mode=json_mode,
        client=client,
    )
