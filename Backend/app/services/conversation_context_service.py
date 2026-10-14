"""Contexto temporal por sesión: historial de mensajes, contexto de recomendación y último producto consultado.

No guarda DNI, direcciones ni otros datos personales. Se pierde al reiniciar la API.
El historial se limita a los últimos MAX_HISTORY mensajes para evitar un contexto excesivo.
"""

from dataclasses import dataclass, field
from typing import List


MAX_HISTORY = 10  # Cuántos turnos se mantienen en memoria por sesión


@dataclass
class MessageTurn:
    role: str   # "user" o "assistant"
    text: str


@dataclass
class RecommendationContext:
    product_choice: str | None = None
    budget: int | None = None


@dataclass
class SessionContext:
    recommendation: RecommendationContext = field(default_factory=RecommendationContext)
    history: List[MessageTurn] = field(default_factory=list)
    last_product_query: str | None = None


class ConversationContextService:
    def __init__(self):
        self._sessions: dict[str, SessionContext] = {}

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _get_session(self, session_id: str | None) -> SessionContext | None:
        return self._sessions.get(session_id) if session_id else None

    def _get_or_create_session(self, session_id: str) -> SessionContext:
        return self._sessions.setdefault(session_id, SessionContext())

    # ─── Historial ─────────────────────────────────────────────────────────────

    def add_turn(self, session_id: str | None, role: str, text: str) -> None:
        """Añade un turno al historial de la sesión, respetando el límite MAX_HISTORY."""
        if not session_id:
            return
        session = self._get_or_create_session(session_id)
        session.history.append(MessageTurn(role=role, text=text))
        if len(session.history) > MAX_HISTORY:
            session.history = session.history[-MAX_HISTORY:]

    def get_history(self, session_id: str | None) -> List[MessageTurn]:
        """Devuelve el historial de mensajes de la sesión (puede estar vacío)."""
        session = self._get_session(session_id)
        return session.history if session else []

    # ─── Último producto / query activa ────────────────────────────────────────

    def set_last_product_query(self, session_id: str | None, query: str | None) -> None:
        if not session_id or not query:
            return
        session = self._get_or_create_session(session_id)
        session.last_product_query = query.strip()

    def get_last_product_query(self, session_id: str | None) -> str | None:
        session = self._get_session(session_id)
        return session.last_product_query if session else None

    # ─── Contexto de recomendación ─────────────────────────────────────────────

    def get_recommendation(self, session_id: str | None) -> RecommendationContext | None:
        session = self._get_session(session_id)
        return session.recommendation if session else None

    def update_recommendation(
        self, session_id: str | None, *, product_choice: str | None = None, budget: int | None = None
    ) -> RecommendationContext:
        if not session_id:
            return RecommendationContext(product_choice=product_choice, budget=budget)
        session = self._get_or_create_session(session_id)
        if product_choice is not None:
            session.recommendation.product_choice = product_choice
        if budget is not None:
            session.recommendation.budget = budget
        return session.recommendation
