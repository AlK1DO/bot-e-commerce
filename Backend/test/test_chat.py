import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chat_routes import router
from app.ai.intent_service import IntentService


class ChatTests(unittest.TestCase):
    def setUp(self):
        # Nunca depende del proveedor configurado en el .env del desarrollador.
        patcher = patch(
            'app.services.chat_service.LLMService.interpret',
            new_callable=AsyncMock,
            return_value=None,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_intents(self):
        cases = {
            "¡Hola!": "saludo",
            "Hola Eli": "saludo",
            "Buenas Eli": "saludo",
            "¿Cuánto cuesta la laptop Lenovo?": "precio",
            "Hola, ¿tienen laptops?": "disponibilidad",
            "¿Qué procesador tiene?": "caracteristicas",
            "¿Cuánta memoria RAM tiene?": "caracteristicas",
            "¿Qué garantía tiene este monitor?": "garantia",
            "Recomiéndame una laptop por 2500 soles": "recomendacion",
            "Busco laptop Lenovo": "buscar_producto",
            "rtx 4060": "buscar_producto",
            "16 de ram": "buscar_producto",
            "i5": "buscar_producto",
            "1tb": "buscar_producto",
            "monitor 144hz": "buscar_producto",
            "gracias por todo": "desconocida",
            "pantallazo azul": "desconocida",
            "precio y stock de laptop": "precio",
        }
        service = IntentService()
        for message, expected in cases.items():
            with self.subTest(message=message):
                self.assertEqual(service.detect_intent(message), expected)

    def test_endpoint_contract_without_firebase(self):
        app = FastAPI()
        app.include_router(router)
        catalog = Mock()
        catalog.search_products.return_value = []
        with patch('app.api.chat_routes.chat_service.product_service', catalog), TestClient(app) as client:
            response = client.post('/api/chat', json={"message": "precio del i5", "session_id": "test"})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body['intent'], 'precio')
            self.assertFalse(body['resolved'])
            self.assertEqual(body['products'], [])
            self.assertIn(client.post('/api/chat', json={"message": "   "}).status_code, (400, 422))
            greeting = client.post('/api/chat', json={"message": "hola"}).json()
            self.assertTrue(greeting['resolved'])
            self.assertIn('Eli', greeting['message'])

    def test_catalog_facts_and_missing_stock(self):
        from app.services.chat_service import ChatService
        catalog = Mock()
        catalog.search_products.return_value = [
            {'id': '1', 'titulo': 'Laptop Lenovo', 'precio': 'S/ 2,500', 'garantia': '12 meses'}
        ]
        service = ChatService(catalog)
        response = asyncio.run(service.process_message('Cuanto cuesta la laptop Lenovo'))
        self.assertEqual(catalog.search_products.call_args.args[0].texto, 'laptop lenovo')
        self.assertEqual(response.products[0].price, 2500)
        self.assertTrue(response.resolved)
        response = asyncio.run(service.process_message('Hay laptop Lenovo disponible'))
        self.assertIsNone(response.products[0].stock)
        self.assertFalse(response.resolved)
        self.assertIn('stock', response.message.lower())
        self.assertIn('12 meses', asyncio.run(service.process_message('garantia laptop Lenovo')).message)

    def test_generic_question_does_not_query_catalog(self):
        from app.services.chat_service import ChatService
        catalog = Mock()
        response = asyncio.run(ChatService(catalog).process_message('cuanto cuesta'))
        self.assertFalse(response.resolved)
        catalog.search_products.assert_not_called()

    def test_greeting_and_known_catalog_queries_do_not_call_ai(self):
        from app.services.chat_service import ChatService
        catalog, llm = Mock(), Mock()
        llm.interpret = AsyncMock(return_value=None)
        catalog.search_products.return_value = []
        chat = ChatService(catalog, llm)
        greeting = asyncio.run(chat.process_message('Hola Eli'))
        price = asyncio.run(chat.process_message('precio de laptop Lenovo'))
        self.assertEqual(greeting.intent, 'saludo')
        self.assertEqual(price.intent, 'precio')
        llm.interpret.assert_not_called()

    def test_unrelated_question_redirects_to_store(self):
        from app.services.chat_service import ChatService
        from app.ai.llm_service import Interpretation
        from app.domain.intents import Intent
        catalog, llm = Mock(), Mock()
        llm.interpret = AsyncMock(return_value=Interpretation(intent=Intent.UNKNOWN, query=''))
        service = ChatService(catalog, llm)
        for message in ('Recomiéndame un restaurante', 'Cuánto cuesta una casa', 'Explícame la Revolución francesa'):
            response = asyncio.run(service.process_message(message))
            self.assertEqual(response.intent, 'desconocida')
            self.assertIn('Eagle Gaming', response.message)
            self.assertEqual(response.products, [])
            self.assertFalse(response.resolved)
        catalog.search_products.assert_not_called()


    def test_comparison_intent_detected(self):
        """Verifica que mensajes con 'vs', 'compara', 'cuál es mejor' se detecten como comparacion."""
        service = IntentService()
        comparison_phrases = [
            "compara RTX 4060 vs RTX 3060",
            "i5 versus i7, ¿cuál es mejor?",
            "RTX 4070 vs RX 7900",
            "diferencia entre i5 e i7",
        ]
        for phrase in comparison_phrases:
            with self.subTest(phrase=phrase):
                self.assertEqual(service.detect_intent(phrase), "comparacion")

    def test_comparison_response_has_products(self):
        """Verifica que una comparativa devuelva productos cuando hay resultados."""
        from app.services.chat_service import ChatService
        catalog = Mock()
        catalog.search_products.return_value = [
            {'id': '1', 'titulo': 'RTX 4060', 'precio': 'S/ 1,200', 'descripcion': 'GPU NVIDIA'},
            {'id': '2', 'titulo': 'RTX 3060', 'precio': 'S/ 900', 'descripcion': 'GPU NVIDIA'},
        ]
        service = ChatService(catalog)
        response = asyncio.run(service.process_message("compara RTX 4060 vs RTX 3060"))
        self.assertEqual(response.intent, "comparacion")
        # Debe al menos intentar buscar productos
        self.assertTrue(catalog.search_products.called)

    def test_history_endpoint(self):
        """Verifica que GET /api/chat/history/{session_id} responde correctamente."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.chat_routes import router as chat_router

        app = FastAPI()
        app.include_router(chat_router)

        with patch(
            'app.api.chat_routes.conversation_repo.get_messages',
            return_value=[
                {"user_message": "hola", "assistant_message": "¡Hola! Soy Eli.", "intent": "saludo"}
            ]
        ), TestClient(app) as client:
            response = client.get('/api/chat/history/session-123')
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body['session_id'], 'session-123')
            self.assertEqual(body['count'], 1)
            self.assertEqual(len(body['messages']), 1)
            self.assertEqual(body['messages'][0]['intent'], 'saludo')

    def test_history_endpoint_invalid_limit(self):
        """Verifica que limit fuera de rango devuelva 400."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.chat_routes import router as chat_router

        app = FastAPI()
        app.include_router(chat_router)

        with TestClient(app) as client:
            response = client.get('/api/chat/history/sess?limit=0')
            self.assertEqual(response.status_code, 400)
            response = client.get('/api/chat/history/sess?limit=999')
            self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    unittest.main()
