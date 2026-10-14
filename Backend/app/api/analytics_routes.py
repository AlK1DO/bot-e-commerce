from fastapi import APIRouter

from app.repositories.conversation_repository import ConversationRepository


router = APIRouter(
    prefix="/api/analytics",
    tags=["Analytics"]
)

conversation_repo = ConversationRepository()


@router.get("/summary")
def get_analytics_summary():
    """Resumen de métricas del chatbot para evaluar el desempeño.

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
    return conversation_repo.get_analytics_summary()
