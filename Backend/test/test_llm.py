import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

import httpx

from app.ai.llm_service import LLMService
from app.ai.providers.base_provider import ProviderError
from app.ai.providers.gemini_provider import GeminiProvider
from app.services.chat_service import ChatService


class LLMTests(unittest.TestCase):
    def test_provider_request(self):
        """GeminiProvider ahora usa AsyncClient; se mockea usando AsyncMock."""
        response = httpx.Response(
            200,
            request=httpx.Request('POST', 'https://example.test'),
            json={
                'candidates': [{
                    'finishReason': 'STOP',
                    'content': {'parts': [{'text': '{"intent":"precio","query":"lenovo"}'}]},
                }]
            },
        )
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__ = AsyncMock(return_value=async_client_mock)
        async_client_mock.__aexit__ = AsyncMock(return_value=False)
        async_client_mock.post = AsyncMock(return_value=response)

        with patch('app.ai.providers.gemini_provider.httpx.AsyncClient', return_value=async_client_mock):
            result = asyncio.run(
                LLMService(GeminiProvider('test-key', 'test-model')).interpret('precio Lenovo')
            )
        self.assertEqual(result.query, 'lenovo')
        call_kwargs = async_client_mock.post.call_args.kwargs
        self.assertEqual(call_kwargs['headers']['x-goog-api-key'], 'test-key')
        self.assertNotIn('test-key', async_client_mock.post.call_args.args[0])

    def test_invalid_output_falls_back(self):
        for raw in ['not json', '{"intent":"inventada","query":"x"}', '{"intent":"precio","query":"x","price":1}']:
            with self.subTest(raw=raw):
                provider = Mock()
                provider.generate_json = AsyncMock(return_value=raw)
                result = asyncio.run(LLMService(provider).interpret('hola'))
                self.assertIsNone(result)

    def test_timeout_and_blocked_output(self):
        async_client_mock = AsyncMock()
        async_client_mock.__aenter__ = AsyncMock(return_value=async_client_mock)
        async_client_mock.__aexit__ = AsyncMock(return_value=False)
        async_client_mock.post = AsyncMock(side_effect=httpx.ReadTimeout('timeout'))
        with patch('app.ai.providers.gemini_provider.httpx.AsyncClient', return_value=async_client_mock):
            result = asyncio.run(LLMService(GeminiProvider('key', 'model')).interpret('hola'))
        self.assertIsNone(result)

        blocked_response = httpx.Response(
            200,
            request=httpx.Request('POST', 'https://example.test'),
            json={'promptFeedback': {'blockReason': 'SAFETY'}},
        )
        async_client_mock2 = AsyncMock()
        async_client_mock2.__aenter__ = AsyncMock(return_value=async_client_mock2)
        async_client_mock2.__aexit__ = AsyncMock(return_value=False)
        async_client_mock2.post = AsyncMock(return_value=blocked_response)
        with patch('app.ai.providers.gemini_provider.httpx.AsyncClient', return_value=async_client_mock2):
            result = asyncio.run(LLMService(GeminiProvider('key', 'model')).interpret('hola'))
        self.assertIsNone(result)

    def test_catalog_is_source_of_price(self):
        provider = Mock()
        provider.generate_json = AsyncMock(return_value='{"intent":"precio","query":"lenovo"}')
        catalog = Mock()
        catalog.search_products.return_value = [{'id': '1', 'titulo': 'Lenovo', 'precio': 2500}]
        result = asyncio.run(
            ChatService(catalog, LLMService(provider)).process_message('Me dices cuánto vale Lenovo')
        )
        self.assertEqual(result.products[0].price, 2500)
        self.assertTrue(any(x in result.message for x in ('2500', '2,500')))
        self.assertEqual(catalog.search_products.call_args.args[0].texto, 'lenovo')

    def test_failure_keeps_local_rules(self):
        provider = Mock()
        provider.generate_json = AsyncMock(side_effect=ProviderError('Unavailable'))
        result = asyncio.run(
            ChatService(llm_service=LLMService(provider)).process_message('hola')
        )
        self.assertEqual(result.intent, 'saludo')


if __name__ == '__main__':
    unittest.main()
