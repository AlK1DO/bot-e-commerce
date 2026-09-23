from fastapi import APIRouter, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService


router = APIRouter(
    prefix="/api/chat",
    tags=["Chat"]
)

chat_service = ChatService()


@router.post("", response_model=ChatResponse)
def send_message(request: ChatRequest):
    try:
        return chat_service.process_message(
            message=request.message,
            session_id=request.session_id
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )