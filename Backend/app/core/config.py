import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
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