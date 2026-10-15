import inspect
import logging
from typing import List

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

    def _get_provider(self) -> BaseProvider:
        """Devuelve el proveedor de IA activo o inicializa Gemini si está configurado.
        Garantiza un tipo BaseProvider no nulo para evitar errores de análisis estático.
        """
        if self.provider is None:
            if settings.AI_PROVIDER != "gemini":
                raise ProviderError("Proveedor de IA no soportado.")
            from app.ai.providers.gemini_provider import GeminiProvider
            self.provider = GeminiProvider(
                settings.GEMINI_API_KEY,
                settings.GEMINI_MODEL,
                settings.GEMINI_TIMEOUT_SECONDS,
            )
        return self.provider

    async def interpret(
        self,
        message: str,
        history: List[dict] | None = None,
    ) -> Interpretation | None:
        """Interpreta el mensaje usando el proveedor de IA de forma asíncrona.

        Acepta opcionalmente el historial de la sesión para resolver referencias
        ambiguas (p. ej. 'ese mismo', 'el anterior').

        Devuelve ``None`` si la IA no está disponible o la respuesta es inválida,
        lo que hace que ChatService caiga de vuelta a las reglas locales.
        """
        if self.provider is None and settings.AI_PROVIDER == "none":
            return None
        try:
            provider = self._get_provider()
            gen_res = provider.generate_json(
                PromptService.interpretation_prompt(history),
                message,
                Interpretation.model_json_schema(),
            )
            raw = await gen_res if inspect.isawaitable(gen_res) else gen_res
            return Interpretation.model_validate_json(raw)
        except (ProviderError, ValidationError, TypeError, AttributeError):
            logging.getLogger(__name__).warning(
                "IA no disponible o respuesta inválida; se usan reglas locales."
            )
            return None

    async def generate_response(
        self,
        user_message: str,
        intent: str,
        products_context: list[dict],
        history: List[dict] | None = None,
    ) -> str | None:
        """Genera una respuesta natural, amigable y vendedora con Gemini,
        grounded en los datos de los productos encontrados en el catálogo.
        Si falla o no hay IA disponible, retorna None para usar el fallback local.
        """
        if self.provider is None and settings.AI_PROVIDER == "none":
            return None
        try:
            provider = self._get_provider()
            system_prompt = PromptService.natural_sales_prompt(
                intent=intent,
                products=products_context,
                history=history,
            )
            res = provider.generate_text(
                system=system_prompt,
                message=user_message,
            )
            response_text = await res if inspect.isawaitable(res) else res
            if isinstance(response_text, str) and response_text.strip():
                return response_text.strip()
            return None
        except (ProviderError, TypeError, AttributeError):
            logging.getLogger(__name__).warning(
                "No se pudo generar respuesta con IA; usando fallback estructurado."
            )
            return None

    async def answer_customer_query(
        self,
        user_message: str,
        history: List[dict] | None = None,
        products_context: list[dict] | None = None,
    ) -> str | None:
        """Responde dudas técnicas, compatibilidad y consultas conversacionales
        como Eli de Eagle Gaming usando Gemini.
        """
        if self.provider is None and settings.AI_PROVIDER == "none":
            return None
        try:
            provider = self._get_provider()
            system_prompt = PromptService.customer_advisor_prompt(
                products=products_context or [],
                history=history,
            )
            res = provider.generate_text(
                system=system_prompt,
                message=user_message,
            )
            response_text = await res if inspect.isawaitable(res) else res
            if isinstance(response_text, str) and response_text.strip():
                return response_text.strip()
            return None
        except Exception:
            logging.getLogger(__name__).warning(
                "No se pudo generar respuesta conversacional con IA."
            )
            return None
