import secrets
from fastapi import APIRouter, Header, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.repositories.conversation_repository import ConversationRepository


limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"]
)

conversation_repo = ConversationRepository()

# Clave efectiva: la del .env en producción; "dev-only" si no se configuró
_EFFECTIVE_KEY = settings.ANALYTICS_API_KEY or "dev-only"


def _require_api_key(x_api_key: str = Header(default="")) -> None:
    """Dependency que valida el header X-Api-Key.
    Usa comparación en tiempo constante para evitar timing attacks.
    """
    if not secrets.compare_digest(x_api_key, _EFFECTIVE_KEY):
        raise HTTPException(
            status_code=401,
            detail="API key inválida o ausente. Incluye el header X-Api-Key.",
        )


@router.get("/summary")
@limiter.limit("30/minute")
def get_analytics_summary(request: Request, x_api_key: str = Header(default="")):
    """Resumen de métricas del chatbot para evaluar el desempeño.

    Requiere header: X-Api-Key: <tu clave>

    Responde al Objetivo Específico 4 de la tesis:
    'Evaluar el funcionamiento del chatbot inteligente mediante indicadores
    relacionados con el tiempo de respuesta, resolución de consultas y
    satisfacción de los usuarios.'

    Campos devueltos:
    - total_messages: total de turnos de conversación registrados
    - resolved_count: mensajes con resolved=True
    - resolution_rate_pct: porcentaje de resolución
    - avg_response_time_ms: tiempo promedio de respuesta en ms
    - min_response_time_ms / max_response_time_ms: rango de tiempos
    - top_intents: los 5 intents más frecuentes con su conteo
    """
    _require_api_key(x_api_key)
    return conversation_repo.get_analytics_summary()
