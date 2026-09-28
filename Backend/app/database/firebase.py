import firebase_admin

from firebase_admin import credentials, firestore

from app.core.config import settings


def initialize_firebase():
    if not firebase_admin._apps:
        credential = credentials.Certificate(
            settings.FIREBASE_CREDENTIALS_PATH
        )

        firebase_admin.initialize_app(credential)
    

def get_firestore():
    initialize_firebase()

    return firestore.client()