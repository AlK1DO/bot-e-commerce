"""Contexto temporal para conversaciones de prueba.

No guarda DNI, direcciones ni otros datos personales. Se pierde al reiniciar la API.
"""

from dataclasses import dataclass


@dataclass
class RecommendationContext:
    product_choice: str | None = None
    budget: int | None = None


class ConversationContextService:
    def __init__(self):
        self._recommendations: dict[str, RecommendationContext] = {}

    def get_recommendation(self, session_id: str | None) -> RecommendationContext | None:
        return self._recommendations.get(session_id) if session_id else None

    def update_recommendation(
        self, session_id: str | None, *, product_choice: str | None = None, budget: int | None = None
    ) -> RecommendationContext:
        if not session_id:
            return RecommendationContext(product_choice=product_choice, budget=budget)
        context = self._recommendations.setdefault(session_id, RecommendationContext())
        if product_choice is not None:
            context.product_choice = product_choice
        if budget is not None:
            context.budget = budget
        return context
