import re

import httpx

from app.ai.providers.base_provider import BaseProvider, ProviderError


class GeminiProvider(BaseProvider):
    def __init__(self, api_key: str, model: str, timeout_seconds: float = 8.0):
        if not api_key or not re.fullmatch(r"[a-zA-Z0-9._-]+", model):
            raise ProviderError("Configura GEMINI_API_KEY y GEMINI_MODEL.")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    async def generate_json(self, system: str, message: str, schema: dict) -> str:
        """Llama a la API de Gemini de forma asíncrona solicitando formato JSON."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                    headers={"x-goog-api-key": self.api_key},
                    json={
                        "systemInstruction": {"parts": [{"text": system}]},
                        "contents": [{"role": "user", "parts": [{"text": message}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "responseJsonSchema": schema,
                            "maxOutputTokens": 2048,
                            "thinkingConfig": {"thinkingBudget": 0},
                        },
                    },
                )
            response.raise_for_status()
            candidate = response.json()["candidates"][0]
            if candidate.get("finishReason") != "STOP":
                raise ProviderError("Gemini no completó la respuesta.")
            text = "".join(
                part.get("text", "")
                for part in candidate["content"]["parts"]
                if not part.get("thought")
            )
            if not text:
                raise ProviderError("Gemini devolvió una respuesta vacía.")
            return text
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError("No se pudo obtener una respuesta válida de Gemini.") from None

    async def generate_text(self, system: str, message: str) -> str:
        """Llama a la API de Gemini de forma asíncrona para generar texto libre conversacional."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                    headers={"x-goog-api-key": self.api_key},
                    json={
                        "systemInstruction": {"parts": [{"text": system}]},
                        "contents": [{"role": "user", "parts": [{"text": message}]}],
                        "generationConfig": {
                            "temperature": 0.7,
                            "maxOutputTokens": 1024,
                            "thinkingConfig": {"thinkingBudget": 0},
                        },
                    },
                )
            response.raise_for_status()
            candidate = response.json()["candidates"][0]
            if candidate.get("finishReason") != "STOP":
                raise ProviderError("Gemini no completó la respuesta.")
            text = "".join(
                part.get("text", "")
                for part in candidate["content"]["parts"]
                if not part.get("thought")
            )
            if not text:
                raise ProviderError("Gemini devolvió una respuesta vacía.")
            return text.strip()
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, AttributeError):
            raise ProviderError("No se pudo obtener una respuesta válida de Gemini.") from None
