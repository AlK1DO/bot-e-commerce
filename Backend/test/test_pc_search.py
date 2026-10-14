import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from app.ai.intent_service import IntentService
from app.domain.search_normalizer import matches_search
from app.services.chat_service import ChatService


class PCSearchTests(unittest.TestCase):
    def test_aliases_match_real_categories(self):
        for query in ('pc armadas', 'pcs armadas', 'computadoras ensambladas', 'pc completo', 'computadora de escritorio'):
            for category in ('PC COMPLETA', 'PC COMPLETO'):
                with self.subTest(query=query, category=category):
                    self.assertTrue(matches_search({'categoria': category}, query))

    def test_excludes_parts_and_keeps_specs(self):
        self.assertFalse(matches_search({'titulo': 'CASE PARA PC ARMADA', 'categoria': 'CASE'}, 'pc armada'))
        self.assertFalse(matches_search({'titulo': 'Procesador i5', 'descripcion': 'para PC completa'}, 'pc completa'))
        self.assertFalse(matches_search({'categoria': 'PC COMPLETA', 'procesador': 'i3'}, 'pc armada i5'))
        self.assertTrue(matches_search({'titulo': 'COMPUTADORA GAMER INTEL CORE I5', 'procesador': 'i5'}, 'pc armada i5'))

    def test_chat_local_fallback(self):
        query = IntentService().extract_product_query('tienen pc armadas?')
        self.assertEqual(query, 'pc completa')
        catalog, llm = Mock(), Mock()
        product = {'id': '1', 'titulo': 'COMPUTADORA PC INTEL I5', 'categoria': 'PC COMPLETO'}
        catalog.search_products.side_effect = lambda filters: [product] if matches_search(product, filters.texto) else []
        llm.interpret = AsyncMock(return_value=None)
        response = asyncio.run(ChatService(catalog, llm).process_message('tienen pc armadas?'))
        self.assertEqual(len(response.products), 1)
        self.assertIsNone(response.products[0].stock)

    def test_natural_queries_keep_only_catalog_terms(self):
        service = IntentService()
        self.assertEqual(service.extract_product_query('Necesito PC completas, ¿tienes?'), 'pc completa')
        self.assertEqual(service.extract_product_query('Venden PC completas?'), 'pc completa')
        self.assertEqual(service.extract_product_query('Tienes procesadores para juegos?'), 'procesador')
        self.assertEqual(service.extract_product_query('Tinen PC armads?'), 'pc completa')
