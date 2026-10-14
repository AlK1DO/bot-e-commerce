import unittest
from unittest.mock import Mock, patch

from app.domain.product_filters import ProductFilters
from app.services.product_service import ProductService
from app.services.catalog_cache import ProductCatalogCache


class ProductServiceTests(unittest.TestCase):
    def setUp(self):
        # Resetear la caché en memoria antes de cada test
        ProductCatalogCache._products = []
        ProductCatalogCache._last_refresh = 0.0

    def test_search_by_category_and_price_range(self):
        sample_products = [
            {"id": "1", "titulo": "Laptop Gamer Acer", "categoria": "Laptop", "precio": 2800, "stock": 5},
            {"id": "2", "titulo": "Laptop Oficina HP", "categoria": "Laptop", "precio": 1500, "stock": 2},
            {"id": "3", "titulo": "Monitor 144Hz LG", "categoria": "Monitor", "precio": 900, "stock": 4},
            {"id": "4", "titulo": "Laptop Premium ASUS", "categoria": "Laptop", "precio": 5200, "stock": 1},
        ]
        with patch("app.repositories.product_repository.get_firestore"):
            service = ProductService()
            service.repository.get_all = Mock(return_value=sample_products)

            # Rango de precio: entre 2000 y 3000 soles
            filters = ProductFilters(categoria="laptop", precio_min=2000, precio_max=3000)
            results = service.search_products(filters)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["id"], "1")

    def test_filter_solo_stock(self):
        sample_products = [
            {"id": "1", "titulo": "RTX 4060", "stock": 3, "precio": 1600},
            {"id": "2", "titulo": "RTX 4070", "stock": 0, "precio": 2600},
        ]
        with patch("app.repositories.product_repository.get_firestore"):
            service = ProductService()
            service.repository.get_all = Mock(return_value=sample_products)

            results = service.search_products(ProductFilters(solo_stock=True))
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["id"], "1")


if __name__ == "__main__":
    unittest.main()
