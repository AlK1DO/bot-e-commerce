from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.repositories.conversation_repository import ConversationRepository


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)

chat_service = ChatService()
conversation_repo = ConversationRepository()


@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest):
    try:
        return await chat_service.process_message(
            message=request.message,
            session_id=request.session_id,
            user_id=request.user_id,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@router.get("/history/{session_id}")
def get_history(session_id: str, limit: int = 50):
    """Devuelve el historial de mensajes de una sesión.
    Útil para restaurar la conversación cuando el usuario logueado vuelve al chat.
    """
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 200")

    messages = conversation_repo.get_messages(session_id=session_id, limit=limit)
    return {
        "session_id": session_id,
        "count": len(messages),
        "messages": messages,
    }