from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat_routes import router as chat_router
from app.api.product_routes import router as product_router
from app.core.config import settings


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend del chatbot inteligente de Eagle Gaming Perú",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(product_router)


@app.get("/")
def root():
    return {
        "message": "Eagle Gaming Chatbot API funcionando"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "environment": settings.APP_ENV
    }