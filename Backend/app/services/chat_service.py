from app.schemas.chat import ChatResponse


class ChatService:

    def process_message(
        self,
        message: str,
        session_id: str | None = None
    ) -> ChatResponse:

        clean_message = message.strip()

        if not clean_message:
            raise ValueError("El mensaje no puede estar vacío.")

        return ChatResponse(
            message=f"Recibí tu mensaje: {clean_message}",
            intent=None,
            resolved=True,
            products=[]
        )