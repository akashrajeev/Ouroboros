import asyncio
from types import SimpleNamespace
import unittest

from pydantic import BaseModel

from browser_use.llm.messages import UserMessage

from muse_spark import ChatMuseSpark


class _AgentOutput(BaseModel):
    current_url: str
    action: str


class _FakeResponses:
    def __init__(self, response):
        self.response = response
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


class _FakeClient:
    def __init__(self, response):
        self.responses = _FakeResponses(response)


class MuseSparkAdapterTests(unittest.TestCase):
    def _build_llm(self, response):
        llm = ChatMuseSpark(
            model="muse-spark-1.3-contributor-free",
            base_url="https://opencode.ai/zen/v1",
            api_key="test-key",
            reasoning_effort="high",
            max_completion_tokens=16384,
        )
        client = _FakeClient(response)
        llm.get_client = lambda: client
        return llm, client

    def test_uses_responses_api_and_returns_text(self):
        response = SimpleNamespace(
            output_text='{"ok":true}',
            status="completed",
            usage=SimpleNamespace(
                input_tokens=11,
                output_tokens=7,
                total_tokens=18,
                input_tokens_details=SimpleNamespace(cached_tokens=3),
            ),
        )
        llm, client = self._build_llm(response)

        result = asyncio.run(llm.ainvoke([UserMessage(content="Open the page")]))

        self.assertEqual(result.completion, '{"ok":true}')
        self.assertEqual(result.usage.prompt_tokens, 11)
        self.assertEqual(result.usage.completion_tokens, 7)
        self.assertEqual(result.usage.prompt_cached_tokens, 3)
        self.assertEqual(len(client.responses.calls), 1)
        call = client.responses.calls[0]
        self.assertEqual(call["model"], "muse-spark-1.3-contributor-free")
        self.assertEqual(call["max_output_tokens"], 16384)
        self.assertEqual(call["reasoning"], {"effort": "high"})
        self.assertEqual(call["input"][0]["role"], "user")
        self.assertEqual(call["input"][0]["content"], "Open the page")

    def test_supports_browser_use_structured_output(self):
        response = SimpleNamespace(
            output_text='{"current_url":"https://example.com","action":"click"}',
            status="completed",
            usage=SimpleNamespace(
                input_tokens=20,
                output_tokens=10,
                total_tokens=30,
                input_tokens_details=None,
            ),
        )
        llm, client = self._build_llm(response)

        result = asyncio.run(
            llm.ainvoke(
                [UserMessage(content="Choose the next browser action")],
                output_format=_AgentOutput,
            )
        )

        self.assertIsInstance(result.completion, _AgentOutput)
        self.assertEqual(result.completion.action, "click")
        self.assertEqual(client.responses.calls[0]["text"]["format"]["type"], "json_schema")
        self.assertTrue(client.responses.calls[0]["text"]["format"]["strict"])


if __name__ == "__main__":
    unittest.main()
