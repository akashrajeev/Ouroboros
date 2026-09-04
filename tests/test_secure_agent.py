import asyncio
import unittest
from types import SimpleNamespace

from browser_use.llm.messages import UserMessage

from privacy.secure_agent import (
    PrivacyBoundaryError,
    assert_no_raw_values,
    build_safe_agent_prompt,
    invoke_safe_model,
    parse_action_plan,
    validate_action,
    _response_text,
)


class _FakeLLM:
    def __init__(self) -> None:
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        return SimpleNamespace(completion='{"action":"noop","target_id":null,"reason":"already complete"}')


class SecureAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.safe_state = {
            "page": {"url": "http://127.0.0.1:8000/demo/checkout.html", "title": "Ouroboros — Checkout"},
            "elements": [
                {
                    "id": "email",
                    "role": "textbox",
                    "name": "Email address",
                    "value": "[EMAIL]",
                    "visible": True,
                    "enabled": True,
                    "detectedTypes": ["EMAIL"],
                },
                {
                    "id": "place-order",
                    "role": "button",
                    "name": "Place test order",
                    "value": "",
                    "visible": True,
                    "enabled": True,
                    "detectedTypes": [],
                },
            ],
        }

    def test_safe_prompt_contains_placeholder_not_raw_value(self) -> None:
        raw = "alex.morgan@example.test"
        prompt = build_safe_agent_prompt("Place the test order", self.safe_state)
        assert_no_raw_values(prompt, (raw,))
        self.assertIn("[EMAIL]", prompt)

    def test_raw_value_is_blocked(self) -> None:
        with self.assertRaises(PrivacyBoundaryError):
            assert_no_raw_values("email=alex.morgan@example.test", ("alex.morgan@example.test",))

    def test_click_action_parses(self) -> None:
        plan = parse_action_plan(
            '{"action":"click","target_id":"place-order","reason":"The checkout is ready."}'
        )
        self.assertEqual(plan.action, "click")
        self.assertEqual(plan.target_id, "place-order")

    def test_sensitive_target_cannot_be_clicked(self) -> None:
        action = parse_action_plan('{"action":"click","target_id":"email","reason":""}')
        with self.assertRaises(PrivacyBoundaryError):
            validate_action(action, self.safe_state)

    def test_safe_button_is_valid(self) -> None:
        action = parse_action_plan('{"action":"click","target_id":"place-order","reason":"submit"}')
        validated = validate_action(action, self.safe_state)
        self.assertEqual(validated, {"action": "click", "target_id": "place-order"})

    def test_browser_use_message_adapter(self) -> None:
        fake_llm = _FakeLLM()
        prompt = build_safe_agent_prompt("Place the test order", self.safe_state)

        result = asyncio.run(invoke_safe_model(fake_llm, prompt))

        self.assertIsInstance(fake_llm.messages, list)
        self.assertEqual(len(fake_llm.messages), 1)
        self.assertIsInstance(fake_llm.messages[0], UserMessage)
        self.assertEqual(_response_text(result), '{"action":"noop","target_id":null,"reason":"already complete"}')


if __name__ == "__main__":
    unittest.main()
