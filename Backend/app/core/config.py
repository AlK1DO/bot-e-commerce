import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    AI_PROVIDER = os.getenv("AI_PROVIDER", "none").strip().lower()
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "").strip()
    GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "8"))
    CATALOG_TTL_SECONDS = int(os.getenv("CATALOG_TTL_SECONDS", "900"))

    APP_NAME = os.getenv(
        "APP_NAME",
        "Eagle Gaming Chatbot"
    )

    APP_ENV = os.getenv(
        "APP_ENV",
        "development"
    )

    FRONTEND_URL = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173"
    )

    FIREBASE_CREDENTIALS_PATH = os.getenv(
        "FIREBASE_CREDENTIALS_PATH",
        "credentials/firebase-service-account.json"
    )


settings = Settings()
