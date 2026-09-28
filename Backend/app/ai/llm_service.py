import logging

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.ai.providers.base_provider import BaseProvider, ProviderError
from app.core.config import settings
from app.domain.intents import Intent
from app.services.prompt_service import PromptService


class Interpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    intent: Intent
    query: str = Field(max_length=300)


class LLMService:
    def __init__(self, provider: BaseProvider | None = None):
        self.provider = provider

    def interpret(self, message: str) -> Interpretation | None:
        if self.provider is None and settings.AI_PROVIDER == "none":
            return None
        try:
            if self.provider is None:
                if settings.AI_PROVIDER != "gemini":
                    raise ProviderError("Proveedor de IA no soportado.")
                from app.ai.providers.gemini_provider import GeminiProvider
                self.provider = GeminiProvider(
                    settings.GEMINI_API_KEY,
                    settings.GEMINI_MODEL,
                    settings.GEMINI_TIMEOUT_SECONDS,
                )
            raw = self.provider.generate_json(
                PromptService.interpretation_prompt(), message,
                Interpretation.model_json_schema(),
            )
            return Interpretation.model_validate_json(raw)
        except (ProviderError, ValidationError):
            logging.getLogger(__name__).warning("IA no disponible o respuesta inválida; se usan reglas locales.")
            return None
