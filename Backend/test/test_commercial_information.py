import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from app.services.chat_service import ChatService


class CommercialInformationTests(unittest.TestCase):
    def setUp(self):
        self.llm = Mock()
        self.llm.interpret = AsyncMock(return_value=None)
        self.chat = ChatService(product_service=Mock(), llm_service=self.llm)

    def test_commercial_questions_do_not_use_gemini_or_catalog(self):
        cases = {
            "Hacen envíos a provincia?": "Lima y provincia",
            "Quiero recoger mi producto": "Cyber Plaza",
            "Cuál es el horario de Ripley?": "11:00 a. m. a 8:00 p. m.",
            "Qué datos necesito para el envío?": "no compartas tu DNI por este chat",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                response = asyncio.run(self.chat.process_message(message))
                self.assertEqual(response.intent, "informacion_comercial")
                self.assertIn(expected, response.message)
                self.assertEqual(response.products, [])
        self.llm.interpret.assert_not_called()
        self.chat.product_service.search_products.assert_not_called()

    def test_unconfirmed_details_are_not_presented_as_final_policy(self):
        payment = asyncio.run(self.chat.process_message("¿Cómo se paga?"))
        location = asyncio.run(self.chat.process_message("¿Dónde queda la tienda?"))
        self.assertFalse(payment.resolved)
        self.assertIn("necesitan confirmación", payment.message)
        self.assertFalse(location.resolved)
        self.assertIn("necesitamos validarlo", location.message)


if __name__ == "__main__":
    unittest.main()
