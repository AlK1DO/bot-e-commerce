import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    AI_PROVIDER = os.getenv("AI_PROVIDER", "none").strip().lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()
    GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "8"))
    CATALOG_TTL_SECONDS = int(os.getenv("CATALOG_TTL_SECONDS", "900"))

    APP_NAME = os.getenv("APP_NAME", "Eagle Gaming Chatbot")
    APP_ENV = os.getenv("APP_ENV", "development")

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # URL de la sección "Arma tu PC" dentro del frontend de Eagle Gaming.
    # Cuando el chatbot detecta que el usuario quiere armar una PC, redirige aquí.
    BUILD_PC_URL = os.getenv("BUILD_PC_URL", "/arma-tu-pc")

    # Número de WhatsApp para soporte y derivación a asesor humano (Perú +51)
    WHATSAPP_NUMBER = os.getenv("WHATSAPP_NUMBER", "51986638034")

    FIREBASE_CREDENTIALS_PATH = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        "credentials/firebase-service-account.json"
    )

    # Clave secreta para proteger el endpoint de métricas.
    # Si está vacía, el endpoint requiere la clave "dev-only" (solo en development).
    # En producción SIEMPRE debes definir esta variable en el .env del servidor.
    ANALYTICS_API_KEY = os.getenv("ANALYTICS_API_KEY", "").strip()


settings = Settings()
