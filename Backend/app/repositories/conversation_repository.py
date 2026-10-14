from datetime import datetime, timezone
from typing import Any
import logging

from app.database.collections import CONVERSATIONS_COLLECTION
from app.database.firebase import get_firestore


class ConversationRepository:
    def __init__(self):
        self._db = None

    def _get_db(self):
        if self._db is None:
            try:
                self._db = get_firestore()
            except Exception as e:
                logging.getLogger(__name__).warning("Firestore no disponible para conversaciones: %s", e)
                return None
        return self._db

    def save_message(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        intent: str | None = None,
        resolved: bool = True,
        products: list[dict[str, Any]] | None = None,
        response_time_ms: float | None = None,
        user_id: str | None = None,
    ) -> bool:
        """Guarda métricas y registro del turno de conversación en Firestore.
        Ocupa menos de 1 KB por mensaje y registra tiempos de respuesta para los
        indicadores de evaluación de la tesis (Objetivo 4).
        """
        if not session_id:
            return False

        db = self._get_db()
        if not db:
            return False

        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            doc_ref = db.collection(CONVERSATIONS_COLLECTION).document(session_id)

            # Guardamos el mensaje en la subcolección de mensajes del session_id
            doc_ref.collection("messages").add({
                "user_message": user_message,
                "assistant_message": assistant_message,
                "intent": intent,
                "resolved": resolved,
                "products_count": len(products) if products else 0,
                "response_time_ms": response_time_ms,
                "timestamp": timestamp,
            })

            # Actualizamos metadata ligera de la sesión
            metadata = {
                "session_id": session_id,
                "last_updated": timestamp,
                "last_intent": intent,
            }
            if user_id:
                metadata["user_id"] = user_id

            doc_ref.set(metadata, merge=True)
            return True
        except Exception as error:
            logging.getLogger(__name__).warning("Error guardando conversación en Firestore: %s", error)
            return False

    def get_messages(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Recupera el historial de mensajes de una sesión (más recientes primero).
        Usado por GET /api/chat/history/{session_id} para que el frontend muestre
        el historial cuando el usuario logueado vuelve a la página.
        """
        if not session_id:
            return []

        db = self._get_db()
        if not db:
            return []

        try:
            messages_ref = (
                db.collection(CONVERSATIONS_COLLECTION)
                .document(session_id)
                .collection("messages")
                .order_by("timestamp")
                .limit_to_last(limit)
            )
            docs = messages_ref.get()
            return [doc.to_dict() for doc in docs]
        except Exception as error:
            logging.getLogger(__name__).warning("Error leyendo historial de Firestore: %s", error)
            return []

    def get_analytics_summary(self) -> dict[str, Any]:
        """Agrega métricas de todos los mensajes guardados para el endpoint de analytics.
        Responde al Objetivo Específico 4 de la tesis: evaluar tiempo de respuesta,
        resolución de consultas e intents más frecuentes.
        Nota: usa un scan completo; aceptable para volumen de tesis (<10k msgs).
        """
        db = self._get_db()
        if not db:
            return {"error": "Firestore no disponible"}

        try:
            sessions = db.collection(CONVERSATIONS_COLLECTION).stream()

            total_messages = 0
            resolved_count = 0
            response_times: list[float] = []
            intent_counts: dict[str, int] = {}

            for session_doc in sessions:
                messages_ref = (
                    db.collection(CONVERSATIONS_COLLECTION)
                    .document(session_doc.id)
                    .collection("messages")
                    .stream()
                )
                for msg in messages_ref:
                    data = msg.to_dict()
                    total_messages += 1

                    if data.get("resolved"):
                        resolved_count += 1

                    rt = data.get("response_time_ms")
                    if rt is not None:
                        response_times.append(float(rt))

                    intent = data.get("intent") or "unknown"
                    intent_counts[intent] = intent_counts.get(intent, 0) + 1

            avg_response_ms = (
                round(sum(response_times) / len(response_times), 2)
                if response_times else 0.0
            )
            resolution_rate = (
                round(resolved_count / total_messages * 100, 1)
                if total_messages else 0.0
            )

            # Top 5 intents
            top_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5]

            return {
                "total_messages": total_messages,
                "resolved_count": resolved_count,
                "resolution_rate_pct": resolution_rate,
                "avg_response_time_ms": avg_response_ms,
                "min_response_time_ms": round(min(response_times), 2) if response_times else 0.0,
                "max_response_time_ms": round(max(response_times), 2) if response_times else 0.0,
                "top_intents": [{"intent": k, "count": v} for k, v in top_intents],
            }
        except Exception as error:
            logging.getLogger(__name__).warning("Error generando analytics: %s", error)
            return {"error": str(error)}
