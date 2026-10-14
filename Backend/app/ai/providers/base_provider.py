from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Error público sin claves ni cuerpo de respuestas del proveedor."""


class BaseProvider(ABC):
    @abstractmethod
    async def generate_json(self, system: str, message: str, schema: dict) -> str:
        """Devuelve texto JSON de forma asíncrona; la capa LLM valida su contenido."""

    @abstractmethod
    async def generate_text(self, system: str, message: str) -> str:
        """Devuelve respuesta en texto libre (lenguaje natural) de forma asíncrona."""
