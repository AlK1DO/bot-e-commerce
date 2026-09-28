import unittest
from unittest.mock import Mock, patch

import httpx

from app.ai.llm_service import LLMService
from app.ai.providers.base_provider import ProviderError
from app.ai.providers.gemini_provider import GeminiProvider
from app.services.chat_service import ChatService


class LLMTests(unittest.TestCase):
    def test_provider_request(self):
        response = httpx.Response(200, request=httpx.Request('POST', 'https://example.test'), json={
            'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': '{"intent":"precio","query":"lenovo"}'}]}}]
        })
        with patch('app.ai.providers.gemini_provider.httpx.post', return_value=response) as post:
            result = LLMService(GeminiProvider('test-key', 'test-model')).interpret('precio Lenovo')
        self.assertEqual(result.query, 'lenovo')
        self.assertEqual(post.call_args.kwargs['headers']['x-goog-api-key'], 'test-key')
        self.assertNotIn('test-key', post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs['timeout'], 8)

    def test_invalid_output_falls_back(self):
        for raw in ['not json', '{"intent":"inventada","query":"x"}', '{"intent":"precio","query":"x","price":1}']:
            with self.subTest(raw=raw):
                provider = Mock()
                provider.generate_json.return_value = raw
                self.assertIsNone(LLMService(provider).interpret('hola'))

    def test_timeout_and_blocked_output(self):
        with patch('app.ai.providers.gemini_provider.httpx.post', side_effect=httpx.ReadTimeout('timeout')):
            self.assertIsNone(LLMService(GeminiProvider('key', 'model')).interpret('hola'))
        response = httpx.Response(200, request=httpx.Request('POST', 'https://example.test'), json={'promptFeedback': {'blockReason': 'SAFETY'}})
        with patch('app.ai.providers.gemini_provider.httpx.post', return_value=response):
            self.assertIsNone(LLMService(GeminiProvider('key', 'model')).interpret('hola'))

    def test_catalog_is_source_of_price(self):
        provider = Mock()
        provider.generate_json.return_value = '{"intent":"precio","query":"lenovo"}'
        catalog = Mock()
        catalog.search_products.return_value = [{'id': '1', 'titulo': 'Lenovo', 'precio': 2500}]
        result = ChatService(catalog, LLMService(provider)).process_message('Me dices cuánto vale Lenovo')
        self.assertEqual(result.products[0].price, 2500)
        self.assertIn('2500.00', result.message)
        self.assertEqual(catalog.search_products.call_args.args[0].texto, 'lenovo')

    def test_failure_keeps_local_rules(self):
        provider = Mock()
        provider.generate_json.side_effect = ProviderError('Unavailable')
        self.assertEqual(ChatService(llm_service=LLMService(provider)).process_message('hola').intent, 'saludo')
