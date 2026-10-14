import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

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

    def save_feedback(
        self,
        session_id: str,
        rating: int,
        comment: str | None = None,
        user_id: str | None = None,
    ) -> bool:
        """Registra la calificación de satisfacción del cliente (1 a 5 estrellas).
        Responde directamente al indicador de 'satisfacción de los usuarios' del
        Objetivo Específico 4 de la tesis.
        """
        if not session_id:
            return False

        db = self._get_db()
        if not db:
            return False

        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            doc_ref = db.collection(CONVERSATIONS_COLLECTION).document(session_id)

            feedback_data = {
                "rating": rating,
                "comment": comment,
                "timestamp": timestamp,
            }
            if user_id:
                feedback_data["user_id"] = user_id

            doc_ref.set({"feedback": feedback_data, "last_updated": timestamp}, merge=True)
            return True
        except Exception as error:
            logging.getLogger(__name__).warning("Error guardando feedback en Firestore: %s", error)
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
        Responde integralmente al Objetivo Específico 4 de la tesis:
        1. Tiempo de respuesta (avg, min, max ms)
        2. Resolución de consultas (total, resueltas, porcentaje)
        3. Satisfacción de los usuarios (promedio estrellas, porcentaje satisfacción positiva)
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
            ratings: list[int] = []
            rating_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}

            for session_doc in sessions:
                s_data = session_doc.to_dict() or {}

                # Feedback de satisfacción
                feedback = s_data.get("feedback")
                if feedback and isinstance(feedback, dict):
                    r = feedback.get("rating")
                    if isinstance(r, (int, float)) and 1 <= int(r) <= 5:
                        int_r = int(r)
                        ratings.append(int_r)
                        rating_counts[int_r] = rating_counts.get(int_r, 0) + 1

                # Mensajes de la subcolección
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

            # Métricas de satisfacción del usuario (Objetivo 4)
            avg_satisfaction = (
                round(sum(ratings) / len(ratings), 2)
                if ratings else 0.0
            )
            # Satisfacción positiva (4 o 5 estrellas)
            positive_ratings = sum(1 for r in ratings if r >= 4)
            satisfaction_pct = (
                round(positive_ratings / len(ratings) * 100, 1)
                if ratings else 0.0
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
                # Indicadores de satisfacción de usuario (CSAT)
                "satisfaction": {
                    "total_ratings": len(ratings),
                    "avg_rating_stars": avg_satisfaction,
                    "satisfaction_rate_pct": satisfaction_pct,
                    "stars_breakdown": rating_counts,
                },
            }
        except Exception as error:
            logging.getLogger(__name__).warning("Error generando analytics: %s", error)
            return {"error": str(error)}

    def export_metrics_csv(self) -> str:
        """Genera un archivo CSV con el detalle de todas las interacciones registradas.
        Permite a los tesistas / administradores importar los datos directos a
        Excel, SPSS o PowerBI para elaborar las tablas y figuras de la tesis.
        """
        db = self._get_db()
        if not db:
            return "error\nFirestore no disponible"

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "session_id",
            "timestamp",
            "intent",
            "resolved",
            "response_time_ms",
            "user_message",
            "assistant_message",
            "feedback_rating",
            "feedback_comment",
        ])

        try:
            sessions = db.collection(CONVERSATIONS_COLLECTION).stream()
            for session_doc in sessions:
                s_data = session_doc.to_dict() or {}
                feedback = s_data.get("feedback") or {}
                fb_rating = feedback.get("rating", "")
                fb_comment = feedback.get("comment", "")

                messages_ref = (
                    db.collection(CONVERSATIONS_COLLECTION)
                    .document(session_doc.id)
                    .collection("messages")
                    .order_by("timestamp")
                    .stream()
                )
                for msg in messages_ref:
                    m = msg.to_dict()
                    writer.writerow([
                        session_doc.id,
                        m.get("timestamp", ""),
                        m.get("intent", ""),
                        "SI" if m.get("resolved") else "NO",
                        m.get("response_time_ms", ""),
                        m.get("user_message", "").replace("\n", " "),
                        m.get("assistant_message", "").replace("\n", " "),
                        fb_rating,
                        fb_comment.replace("\n", " "),
                    ])

            return output.getvalue()
        except Exception as error:
            logging.getLogger(__name__).warning("Error exportando métricas CSV: %s", error)
            return f"error\n{error}"

    def cleanup_old_conversations(self, days: int = 30) -> dict[str, Any]:
        """Elimina sesiones inactivas más antiguas de N días en Firestore.
        Evita saturar el límite de almacenamiento gratuito de Firebase.
        """
        db = self._get_db()
        if not db:
            return {"error": "Firestore no disponible"}

        if days < 1:
            days = 1

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()

        deleted_sessions = 0
        deleted_messages = 0

        try:
            sessions = db.collection(CONVERSATIONS_COLLECTION).stream()
            for session_doc in sessions:
                data = session_doc.to_dict() or {}
                last_updated = data.get("last_updated") or ""

                if last_updated and last_updated < cutoff_iso:
                    # Borrar subcolección de mensajes primero
                    msgs = (
                        db.collection(CONVERSATIONS_COLLECTION)
                        .document(session_doc.id)
                        .collection("messages")
                        .stream()
                    )
                    for m in msgs:
                        m.reference.delete()
                        deleted_messages += 1

                    # Borrar documento de sesión
                    session_doc.reference.delete()
                    deleted_sessions += 1

            return {
                "status": "ok",
                "days_threshold": days,
                "deleted_sessions": deleted_sessions,
                "deleted_messages": deleted_messages,
            }
        except Exception as error:
            logging.getLogger(__name__).warning("Error durante purga de conversaciones: %s", error)
            return {"error": str(error)}
