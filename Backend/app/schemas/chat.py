from typing import Optional, List
from pydantic import BaseModel


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


class ChatResponse(BaseModel):
    message: str
    intent: Optional[str] = None
    resolved: bool = True
    products: List[ProductSummary] = []
    quick_replies: List[str] = []
    response_time_ms: Optional[float] = None  # Métrica clave para el Objetivo 4 de la tesis
