"""Contexto temporal por sesión: historial de mensajes, contexto de recomendación y último producto consultado.

No guarda DNI, direcciones ni otros datos personales. Se pierde al reiniciar la API.
El historial se limita a los últimos MAX_HISTORY mensajes para evitar un contexto excesivo.
Las sesiones sin actividad por más de SESSION_TTL_SECONDS se eliminan automáticamente
para evitar consumo excesivo de memoria (protección ante muchas sesiones simultáneas).
"""

import time
from dataclasses import dataclass, field
from typing import List


MAX_HISTORY = 10          # Turnos máximos por sesión en memoria
SESSION_TTL_SECONDS = 1800  # 30 minutos de inactividad → se descarta la sesión
MAX_SESSIONS = 2000         # Si se supera este número se hace limpieza agresiva


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
    last_products: list[dict] = field(default_factory=list)
    last_active: float = field(default_factory=time.monotonic)


class ConversationContextService:
    def __init__(self):
        self._sessions: dict[str, SessionContext] = {}

    # ─── Limpieza por TTL ──────────────────────────────────────────────────────

    def _evict_expired(self) -> None:
        """Elimina sesiones inactivas. Se llama en cada acceso para evitar hilo extra."""
        now = time.monotonic()
        expired = [
            sid for sid, ctx in self._sessions.items()
            if now - ctx.last_active > SESSION_TTL_SECONDS
        ]
        for sid in expired:
            del self._sessions[sid]

        # Limpieza agresiva si se superó el máximo: elimina las más antiguas
        if len(self._sessions) > MAX_SESSIONS:
            sorted_by_age = sorted(self._sessions.items(), key=lambda x: x[1].last_active)
            to_remove = len(self._sessions) - MAX_SESSIONS
            for sid, _ in sorted_by_age[:to_remove]:
                del self._sessions[sid]

    # ─── Helpers ───────────────────────────────────────────────────────────────

    def _get_session(self, session_id: str | None) -> SessionContext | None:
        if not session_id:
            return None
        self._evict_expired()
        session = self._sessions.get(session_id)
        if session:
            session.last_active = time.monotonic()
        return session

    def _get_or_create_session(self, session_id: str) -> SessionContext:
        self._evict_expired()
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionContext()
        session = self._sessions[session_id]
        session.last_active = time.monotonic()
        return session

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

    def set_last_products(self, session_id: str | None, products: list[dict]) -> None:
        if not session_id or not products:
            return
        session = self._get_or_create_session(session_id)
        session.last_products = products[:5]

    def get_last_products(self, session_id: str | None) -> list[dict]:
        session = self._get_session(session_id)
        return session.last_products if session else []

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
