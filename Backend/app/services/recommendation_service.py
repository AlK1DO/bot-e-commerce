from app.domain.product_filters import ProductFilters
from app.domain.recommendation_rules import is_processor_product, processor_query


class RecommendationService:
    def __init__(self, product_service):
        self.product_service = product_service

    def processor_options(self, message: str) -> list[dict]:
        products = self.product_service.search_products(
            ProductFilters(texto=processor_query(message) or None)
        )
        # Son opciones para precisar la consulta, no un ranking de rendimiento.
        return [p for p in products if is_processor_product(p)][:5]
