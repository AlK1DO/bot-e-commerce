import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.analytics_routes import router as analytics_router
from app.api.chat_routes import router as chat_router
from app.api.product_routes import router as product_router
from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Rate Limiter global ────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# En producción ocultamos la documentación interactiva Swagger/OpenAPI para evitar escaneo
is_production = settings.APP_ENV == "production"

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend del chatbot inteligente de Eagle Gaming Perú",
    version="1.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

# Registrar el limiter y su handler de error en la app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ─── Middleware de Cabeceras de Seguridad HTTP (Security Headers) ─────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Añade cabeceras estándar de protección contra MIME sniffing, Clickjacking y XSS."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Server"] = "EagleGaming-API"
    return response


# ─── Manejador Global de Errores Inesperados (Anti-Stack Trace Leak) ──────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Captura cualquier excepción no manejada para registrarla internamente sin
    revelar detalles de código ni rutas de archivos locales en la respuesta HTTP.
    """
    logger.error("Error no controlado en %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Por favor, intente más tarde."},
    )


# ─── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(product_router)
app.include_router(analytics_router)

# La carpeta de prueba /preview solo se monta si existe y NO estamos en producción
preview_dir = Path(__file__).resolve().parent.parent / "preview"
if preview_dir.is_dir() and not is_production:
    app.mount("/preview", StaticFiles(directory=preview_dir, html=True), name="preview")


@app.get("/")
def root():
    return {"message": "Eagle Gaming Chatbot API funcionando"}


@app.get("/health")
def health():
    return {"status": "ok", "environment": settings.APP_ENV}
