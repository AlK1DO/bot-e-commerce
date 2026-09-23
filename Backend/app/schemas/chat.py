from typing import Optional, List
from pydantic import BaseModel


class ProductSummary(BaseModel):
    id: str
    name: str
    price: float
    stock: int
    image_url: Optional[str] = None
    product_url: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    message: str
    intent: Optional[str] = None
    resolved: bool = True
    products: List[ProductSummary] = []