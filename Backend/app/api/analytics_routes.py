import secrets
from typing import Optional
from fastapi import APIRouter, Header, HTTPException, Query, Request, Response
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


def _verify_auth(x_api_key: str = "", query_api_key: Optional[str] = None) -> None:
    """Valida la clave por header X-Api-Key o por query param ?api_key=.
    Usa comparación en tiempo constante para evitar timing attacks.
    """
    key_to_check = x_api_key or query_api_key or ""
    if not secrets.compare_digest(key_to_check, _EFFECTIVE_KEY):
        raise HTTPException(
            status_code=401,
            detail="API key de administrador inválida o ausente. Incluye el header X-Api-Key o el parámetro ?api_key=.",
        )


@router.get("/summary")
@limiter.limit("30/minute")
def get_analytics_summary(
    request: Request,
    x_api_key: str = Header(default=""),
    api_key: Optional[str] = Query(default=None),
):
    """Resumen de métricas del chatbot para evaluar el desempeño (Solo Administrador / Tesistas).

    Requiere autenticación mediante header `X-Api-Key` o parámetro `?api_key=`.

    Responde directamente al Objetivo Específico 4 de la tesis:
    - Indicador 1: Tiempo de respuesta (promedio, min, max en ms).
    - Indicador 2: Resolución de consultas (total, resueltas, porcentaje).
    - Indicador 3: Satisfacción de los usuarios (calificación promedio, desglose por estrellas).
    """
    _verify_auth(x_api_key=x_api_key, query_api_key=api_key)
    return conversation_repo.get_analytics_summary()


@router.get("/export")
@limiter.limit("10/minute")
def export_metrics(
    request: Request,
    x_api_key: str = Header(default=""),
    api_key: Optional[str] = Query(default=None),
    format: str = Query(default="csv", regex="^(csv)$"),
):
    """Descarga los datos completos de las interacciones en formato CSV (Solo Administrador / Tesistas).
    
    Permite abrir el archivo en Excel o SPSS para elaborar las tablas y gráficos
    estadísticos para la sustentación de la tesis.

    Ejemplo de descarga directa en navegador:
    GET /api/analytics/export?api_key=tu-clave
    """
    _verify_auth(x_api_key=x_api_key, query_api_key=api_key)
    csv_content = conversation_repo.export_metrics_csv()

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=metricas_chatbot_eagle_gaming.csv"
        },
    )


@router.delete("/cleanup")
@limiter.limit("5/minute")
def cleanup_old_data(
    request: Request,
    x_api_key: str = Header(default=""),
    api_key: Optional[str] = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
):
    """Elimina conversaciones de prueba o sesiones inactivas anteriores a N días (Solo Administrador).
    
    Protege el límite de almacenamiento de Firebase Firestore eliminando historial antiguo.
    """
    _verify_auth(x_api_key=x_api_key, query_api_key=api_key)
    return conversation_repo.cleanup_old_conversations(days=days)
