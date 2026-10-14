import re
from typing import Optional, List
from pydantic import BaseModel, field_validator, model_validator


# Máximo de caracteres permitidos en un mensaje de chat.
# Protege contra abuso de tokens de Gemini y ataques de payload masivo.
MESSAGE_MAX_LENGTH = 500

# Regex para session_id válido: solo letras, números, guiones y guiones bajos.
# Previene path traversal y caracteres raros en IDs de Firestore.
_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


class ProductSummary(BaseModel):
    id: str
    name: str
    summary: Optional[str] = None
    price: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None  # Para vincular cuando el usuario inicia sesión en Eagle Gaming

    @field_validator("message")
    @classmethod
    def message_must_be_valid(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("El mensaje no puede estar vacío.")
        if len(stripped) > MESSAGE_MAX_LENGTH:
            raise ValueError(
                f"El mensaje es demasiado largo. Máximo {MESSAGE_MAX_LENGTH} caracteres."
            )
        return stripped

    @field_validator("session_id")
    @classmethod
    def session_id_must_be_safe(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not _SESSION_ID_RE.match(v):
            raise ValueError(
                "session_id inválido. Solo se permiten letras, números, guiones y guiones bajos (máx. 128 caracteres)."
            )
        return v


class ChatResponse(BaseModel):
    message: str
    intent: Optional[str] = None
    resolved: bool = True
    products: List[ProductSummary] = []
    quick_replies: List[str] = []
    response_time_ms: Optional[float] = None  # Métrica clave para el Objetivo 4 de la tesis


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int  # 1 a 5 estrellas
    comment: Optional[str] = None
    user_id: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def rating_in_range(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("La calificación debe estar entre 1 y 5 estrellas.")
        return v

    @field_validator("comment")
    @classmethod
    def comment_max_len(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v.strip()) > 300:
            raise ValueError("El comentario no puede superar 300 caracteres.")
        return v.strip() if v else None

    @field_validator("session_id")
    @classmethod
    def session_id_valid(cls, v: str) -> str:
        v = v.strip()
        if not _SESSION_ID_RE.match(v):
            raise ValueError("session_id inválido.")
        return v


class FeedbackResponse(BaseModel):
    status: str
    message: str
    session_id: str
    rating: int
