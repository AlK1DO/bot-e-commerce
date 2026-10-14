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


    def test_human_support_intent_and_response(self):
        """Verifica que solicitudes de asesor humano o WhatsApp se detecten y respondan con el número 986638034."""
        from app.services.chat_service import ChatService
        service = IntentService()
        phrases = [
            "quiero hablar con un asesor",
            "pásame con un humano",
            "comunicarme con una persona",
            "cuál es el número de whatsapp",
            "atención al cliente soporte",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertEqual(service.detect_intent(phrase), "asesor_humano")

        chat = ChatService(Mock())
        response = asyncio.run(chat.process_message("quiero hablar con un asesor"))
        self.assertEqual(response.intent, "asesor_humano")
        self.assertTrue(response.resolved)
        self.assertIn("986 638 034", response.message)
        self.assertIn("wa.me/51986638034", response.message)

    def test_build_pc_intent_and_response(self):
        """Verifica que solicitudes de armar PC redirijan a la sección /arma-tu-pc."""
        from app.services.chat_service import ChatService
        service = IntentService()
        phrases = [
            "cómo armar mi pc",
            "quiero armar una pc",
            "arma tu pc",
            "cómo configuro una pc personalizada",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                self.assertEqual(service.detect_intent(phrase), "armar_pc")

        chat = ChatService(Mock())
        response = asyncio.run(chat.process_message("cómo armar mi pc gamer"))
        self.assertEqual(response.intent, "armar_pc")
        self.assertTrue(response.resolved)
        self.assertIn("/arma-tu-pc", response.message)

    def test_feedback_endpoint(self):
        """Verifica que POST /api/chat/feedback guarde calificaciones y valide rango 1-5."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.chat_routes import router as chat_router

        app = FastAPI()
        app.include_router(chat_router)

        with patch(
            'app.api.chat_routes.conversation_repo.save_feedback',
            return_value=True
        ), TestClient(app) as client:
            # Calificación válida 5 estrellas
            res = client.post('/api/chat/feedback', json={
                "session_id": "sess-test-1",
                "rating": 5,
                "comment": "Excelente atención de Eli"
            })
            self.assertEqual(res.status_code, 200)
            self.assertEqual(res.json()["status"], "success")
            self.assertEqual(res.json()["rating"], 5)

            # Calificación inválida (fuera de rango 1-5)
            res_bad = client.post('/api/chat/feedback', json={
                "session_id": "sess-test-1",
                "rating": 6
            })
            self.assertEqual(res_bad.status_code, 422)

    def test_analytics_export_and_auth(self):
        """Verifica la exportación CSV y la autenticación de administrador."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.analytics_routes import router as analytics_router

        app = FastAPI()
        app.include_router(analytics_router)

        with patch(
            'app.api.analytics_routes.conversation_repo.export_metrics_csv',
            return_value="session_id,timestamp,intent\nsess-1,2026-10-14,precio"
        ), TestClient(app) as client:
            # Sin autenticación debe fallar 401
            res_no_auth = client.get('/api/analytics/export')
            self.assertEqual(res_no_auth.status_code, 401)

            # Con API key válida debe responder CSV
            res_auth = client.get('/api/analytics/export?api_key=dev-only')
            self.assertEqual(res_auth.status_code, 200)
            self.assertIn("text/csv", res_auth.headers["content-type"])
            self.assertIn("sess-1", res_auth.text)


if __name__ == '__main__':
    unittest.main()
