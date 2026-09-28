from abc import ABC, abstractmethod


class ProviderError(Exception):
    """Error público sin claves ni cuerpo de respuestas del proveedor."""


class BaseProvider(ABC):
    @abstractmethod
    def generate_json(self, system: str, message: str, schema: dict) -> str:
        """Devuelve texto JSON; la capa LLM valida su contenido."""
