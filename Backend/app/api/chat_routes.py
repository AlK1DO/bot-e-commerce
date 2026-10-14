from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.chat import ChatRequest, ChatResponse, FeedbackRequest, FeedbackResponse
from app.services.chat_service import ChatService
from app.repositories.conversation_repository import ConversationRepository


limiter = Limiter(key_func=get_remote_address)

router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)

chat_service = ChatService()
conversation_repo = ConversationRepository()


@router.post("", response_model=ChatResponse)
@limiter.limit("20/minute")
async def send_message(request: Request, body: ChatRequest):
    """Procesa un mensaje del usuario.
    Límite: 20 mensajes por minuto por IP.
    """
    try:
        return await chat_service.process_message(
            message=body.message,
            session_id=body.session_id,
            user_id=body.user_id,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))


@router.get("/history/{session_id}")
@limiter.limit("10/minute")
def get_history(request: Request, session_id: str, limit: int = 50):
    """Devuelve el historial de mensajes de una sesión.
    Límite: 10 consultas por minuto por IP.
    """
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 200")

    messages = conversation_repo.get_messages(session_id=session_id, limit=limit)
    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": messages,
    }


@router.post("/feedback", response_model=FeedbackResponse)
@limiter.limit("10/minute")
def submit_feedback(request: Request, body: FeedbackRequest):
    """Registra la calificación de satisfacción del cliente (1 a 5 estrellas).
    Permite evaluar el indicador de 'satisfacción de los usuarios' del
    Objetivo Específico 4 de la tesis.
    """
    success = conversation_repo.save_feedback(
        session_id=body.session_id,
        rating=body.rating,
        comment=body.comment,
        user_id=body.user_id,
    )
    if not success:
        raise HTTPException(
            status_code=500,
            detail="No se pudo registrar la calificación en la base de datos."
        )
    return FeedbackResponse(
        status="success",
        message="¡Muchas gracias por calificar la atención!",
        session_id=body.session_id,
        rating=body.rating,
    )