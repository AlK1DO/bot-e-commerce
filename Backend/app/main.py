from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pathlib import Path
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api.chat_routes import router as chat_router
from app.api.product_routes import router as product_router
from app.api.analytics_routes import router as analytics_router
from app.core.config import settings


# ─── Rate Limiter global ────────────────────────────────────────────────────
# Límites por IP. Ajusta los valores en .env si es necesario.
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend del chatbot inteligente de Eagle Gaming Perú",
    version="1.0.0",
)

# Registrar el limiter y su handler de error en la app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(product_router)
app.include_router(analytics_router)
app.mount(
    '/preview',
    StaticFiles(directory=Path(__file__).resolve().parent.parent / 'preview', html=True),
    name='preview',
)


@app.get("/")
def root():
    return {"message": "Eagle Gaming Chatbot API funcionando"}


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.APP_ENV}
