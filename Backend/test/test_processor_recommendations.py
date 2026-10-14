import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from app.ai.llm_service import Interpretation
from app.domain.intents import Intent
from app.services.chat_service import ChatService


class ProcessorRecommendationTests(unittest.TestCase):
    def test_gaming_request_returns_catalog_candidates(self):
        catalog = Mock()
        catalog.search_products.return_value = [
            {'id': 'cpu', 'titulo': 'PROCESADOR INTEL CORE I5', 'precio': 500},
            {'id': 'pc', 'titulo': 'PC GAMER I5', 'categoria': 'PC COMPLETA'},
            {'id': 'out', 'titulo': 'PROCESADOR AMD', 'stock': 0},
        ]
        for intent in [Intent.RECOMMENDATION, Intent.PRODUCT_SEARCH]:
            llm = Mock()
            llm.interpret = AsyncMock(return_value=Interpretation(intent=intent, query='procesador juego'))
            result = asyncio.run(ChatService(catalog, llm).process_message('un procesador para juego'))
            self.assertEqual([p.id for p in result.products], ['cpu'])
            self.assertEqual(result.intent, 'recomendacion')
            self.assertFalse(result.resolved)
            self.assertIn('placa madre', result.message)
            self.assertIsNone(result.products[0].stock)

    def test_local_fallback_and_no_candidates(self):
        catalog, llm = Mock(), Mock()
        catalog.search_products.return_value = []
        llm.interpret = AsyncMock(return_value=None)
        result = asyncio.run(ChatService(catalog, llm).process_message('procesador para jugar'))
        self.assertEqual(result.intent, 'recomendacion')
        self.assertFalse(result.resolved)
        self.assertIn('No encontré', result.message)

    def test_availability_question_about_gaming_processors_is_a_recommendation(self):
        catalog, llm = Mock(), Mock()
        catalog.search_products.return_value = []
        llm.interpret = AsyncMock(return_value=None)
        result = asyncio.run(ChatService(catalog, llm).process_message('tienes procesadores para juegos?'))
        self.assertEqual(result.intent, 'recomendacion')
        llm.interpret.assert_not_called()
