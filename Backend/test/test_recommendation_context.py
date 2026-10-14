import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from app.services.chat_service import ChatService


class RecommendationContextTests(unittest.TestCase):
    def test_budget_keeps_the_previous_recommendation_context(self):
        catalog, llm = Mock(), Mock()
        llm.interpret = AsyncMock(return_value=None)
        catalog.search_products.return_value = [
            {"id": "l1", "titulo": "Laptop para trabajo", "categoria": "laptops", "precio": 5500}
        ]
        chat = ChatService(catalog, llm)
        first = asyncio.run(chat.process_message("Recomiéndame una laptop", session_id="s-1"))
        second = asyncio.run(chat.process_message("Para ingeniería y trabajo, presupuesto de 6000 soles", session_id="s-1"))
        self.assertIn("presupuesto", first.message)
        self.assertIn("opciones", second.message)
        self.assertEqual(catalog.search_products.call_args.args[0].categoria, "laptop")
        self.assertEqual(catalog.search_products.call_args.args[0].precio_max, 6000)
        self.assertEqual(second.products[0].id, "l1")
        llm.interpret.assert_not_called()

    def test_laptop_or_pc_becomes_a_clear_question(self):
        llm = Mock()
        llm.interpret = AsyncMock(return_value=None)
        chat = ChatService(Mock(), llm)
        response = asyncio.run(chat.process_message("¿Qué me recomiendas, laptop o PC?", session_id="s-2"))
        self.assertIn("Cuál prefieres", response.message)
        self.assertEqual(response.products, [])


if __name__ == "__main__":
    unittest.main()
